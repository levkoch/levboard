"""
ingest_history.py

Ingests Spotify extended streaming history JSON files into a local SQLite
database. Run this once (or re-run to incrementally add new history files).
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import LEVBOARD_SHEET
from spreadsheet import Spreadsheet
from model import spotistats

DB_PATH = 'listens.db'

CREATE_LISTENS = """
CREATE TABLE IF NOT EXISTS listens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              INTEGER NOT NULL,           -- epoch milliseconds (UTC)
    track_id        TEXT,                       -- Spotify track id (no prefix)
    statsfm_id      TEXT,                       -- stats.fm track id (NULL if unknown)
    track_name      TEXT,
    artist_name     TEXT,
    ms_played       INTEGER NOT NULL,
    UNIQUE(ts, track_id, ms_played)             -- dedup on re-ingest
)
"""

CREATE_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_listens_track_id   ON listens(track_id)',
    'CREATE INDEX IF NOT EXISTS idx_listens_statsfm_id ON listens(statsfm_id)',
    'CREATE INDEX IF NOT EXISTS idx_listens_ts         ON listens(ts)',
    'CREATE INDEX IF NOT EXISTS idx_listens_artist     ON listens(artist_name)',
]


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_LISTENS)
    for idx in CREATE_INDEXES:
        conn.execute(idx)
    conn.commit()


# ── Parsing ───────────────────────────────────────────────────────────────────


def _extract_track_id(uri: str | None) -> str | None:
    """chop out the spotify:track: thing"""
    if uri and uri.startswith('spotify:track:'):
        return uri.split(':')[-1]
    return None


ids_cache: Optional[dict[str, str]] = None


def default_statsfm_links() -> None:
    # max limit for this request is 500 songs and not the 10,000 like others have
    address = 'https://api.stats.fm/api/v1/users/lev/top/tracks?limit=500'

    r = spotistats._get_address(address)
    additions: list[dict] = r.json()['items']
    items: list[dict] = additions
    print('*', end='')

    offset = 500
    while len(additions) > 0:
        address = (
            f'https://api.stats.fm/api/v1/users/lev/top/tracks'
            f'?limit=500&offset={offset}'
        )
        r = spotistats._get_address(address)
        additions = r.json()['items']
        items.extend(additions)
        offset += 500
        print('*', end='')

    print('')
    print(f'{len(items)} statsfm pairings loaded')

    for group in items:
        try:
            for spotify_id in group['track']['externalIds']['spotify']:
                ids_cache[str(spotify_id)] = str(group['track']['id'])
        except KeyError:
            print(f'error processing {group}')


def load_spotify_to_statsfm_links() -> None:
    print('updating cached id links')

    global ids_cache
    ids_cache = {}

    sheet = Spreadsheet(LEVBOARD_SHEET)
    rows = sheet.get_range('Songs!C2:E')['values']

    for row in rows:
        if len(row) < 3:
            continue
        statsfm_str, sheet_id, spotify_str = row
        if not statsfm_str or not spotify_str:
            continue
        statsfm_id = statsfm_str.split(', ')[0].strip()
        for spotify_id in spotify_str.split(', '):
            if spotify_id.strip() in ids_cache:
                print(f'duplicate spotify uri {spotify_id} detected')
            ids_cache[spotify_id.strip()] = statsfm_id

    print(
        f'loaded {len(ids_cache)} spotify -> statsfm id mappings from spreadsheet'
    )


def update_spreadsheet_with_spotify_uris(db_path: str) -> None:
    """
    makes some educated guessesa about what the stats fm id is based on what we have in our spreadsheet.
    this will clobber songs where the main artist has two distinct songs which are named the same thing.
    madonna with "frozen" remix and raye with "fin." i dunno why u did this to me...
    """

    conn = sqlite3.connect(db_path)
    result = conn.execute(
        """
        SELECT DISTINCT track_id FROM listens
    """
    ).fetchall()
    conn.close()

    all_streamed: set[str] = {row[0] for row in result}
    print(f'{len(all_streamed)} overall spotify ids streamed')

    sheet = Spreadsheet(LEVBOARD_SHEET)
    rows = sheet.get_range('URIs!A2:F')['values']
    out = []

    # snatch up spotify uris from stats fm

    load_spotify_to_statsfm_links()
    statsfm_to_spotify: dict[str, set[str]] = {}

    for (spotify_id, statsfm_id) in ids_cache.items():
        if statsfm_id not in statsfm_to_spotify:
            statsfm_to_spotify[statsfm_id] = {spotify_id}
        else:
            statsfm_to_spotify[statsfm_id].add(spotify_id)

    print(f'{len(statsfm_to_spotify)} pairings found')

    # snatch up ids from matching title + artists (not as great for collaborative songs
    # or songs that have weird formatting, like a lot do.)

    conn = sqlite3.connect(db_path)
    result = conn.execute(
        """
        SELECT DISTINCT track_name, artist_name, track_id FROM listens
    """
    ).fetchall()
    conn.close()

    title_to_uris = {}

    for row in result:
        group = (row[0].lower(), row[1].lower())
        if group in title_to_uris:
            title_to_uris[group].add(row[2])
        else:
            title_to_uris[group] = {row[2]}

    for row in rows:
        try:
            (
                title,
                var_ind,
                statsfm_str,
                sheet_id,
                spotify_str,
                song_artists,
            ) = row
        except ValueError as e:
            print(f'error processing {row}')
            raise e

        spotify_ids = set(
            s.strip() for s in spotify_str.split(', ') if s.strip()
        )
        statsfm_ids = set(
            s.strip() for s in statsfm_str.split(', ') if s.strip()
        )

        # look for ids which we could possibly add that statsfm already tied for us
        # (for some reason they only display one or none ids per song, which is annoying)
        for statsfm_id in statsfm_ids:
            spotify_ids |= statsfm_to_spotify.get(statsfm_id, set())

        if (title.lower(), song_artists.lower()) in title_to_uris:
            spotify_ids |= title_to_uris[(title.lower(), song_artists.lower())]

        if ', ' in song_artists:
            spotify_ids |= title_to_uris.get(
                (title.lower(), song_artists.split(', ')[0].lower()), set()
            )

        # take out all ids which we have not streamed (dead weight)
        spotify_ids &= all_streamed

        out.append(
            [
                title,
                var_ind,
                statsfm_str,
                sheet_id,
                ', '.join(spotify_ids),
                song_artists,
            ]
        )

    range = f'URIs!A2:F{len(out) + 1}'
    sheet.delete_range(range)
    sheet.update_range(range, out)

    print('updated loaded ids')


def spotify_to_statsfm(spotify_id: str) -> str | None:
    """
    Map a Spotify track id to a stats.fm track id.
    Fill this in with your own lookup logic; return None if unknown.
    """
    # converts to the closest song id that it's associated with.
    # this will preserve variants.

    global ids_cache

    if ids_cache is None:
        load_spotify_to_statsfm_links()

    return ids_cache.get(spotify_id)


def parse_entry(entry: dict) -> dict | None:
    """Return a flat row dict, or None if the entry is not a music track."""
    # skip podcasts / audiobooks (no track uri)
    uri = entry.get('spotify_track_uri')
    if not uri:
        return None

    # filter out things we listened to less than 30 seconds (30_000 ms)
    ms_played = entry.get('ms_played', 0)
    if ms_played < 30_000:
        return None

    raw_ts = entry.get('ts', '')
    # "2021-11-11T01:27:32Z" -> epoch milliseconds
    ts_ms = int(
        datetime.strptime(raw_ts, '%Y-%m-%dT%H:%M:%SZ').timestamp() * 1000
    )

    spotify_id = _extract_track_id(uri)

    # mark hacked me :(
    BANNED_IDS = {'2QLGkiJxugt03yGKVPt3u5'}
    if spotify_id in BANNED_IDS:
        return None

    statsfm_id = spotify_to_statsfm(spotify_id) if spotify_id else None

    return {
        'ts': ts_ms,
        'track_id': spotify_id,
        'statsfm_id': statsfm_id,
        'track_name': entry.get('master_metadata_track_name'),
        'artist_name': entry.get('master_metadata_album_artist_name'),
        'ms_played': entry.get('ms_played', 0),
    }


def ingest_file(conn: sqlite3.Connection, path: Path) -> int:
    """Ingest one JSON file. Returns total row count for file."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    rows = [r for entry in data if (r := parse_entry(entry)) is not None]

    with conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO listens
                (ts, track_id, statsfm_id, track_name, artist_name, ms_played)
            VALUES
                (:ts, :track_id, :statsfm_id, :track_name, :artist_name, :ms_played)
            """,
            rows,
        )

    return len(rows)


def ingest_files(db_path: str, json_files: list[Path]) -> None:
    conn = sqlite3.connect(db_path)
    init_db(conn)

    total_attempted = 0
    for path in json_files:
        attempted = ingest_file(conn, path)
        print(
            f'   ({path.name.split("_")[2][0]}) '
            f'{"_".join(path.name.split("_")[3:])}: {attempted} rows inserted'
        )
        total_attempted += attempted

    conn.close()
    print(
        f"\ninsertion complete: {total_attempted} total rows into '{db_path}'"
    )


def get_missing_songs(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    result = conn.execute(
        """
        SELECT track_name, artist_name, track_id, COUNT(*) as plays
        FROM listens
        WHERE statsfm_id IS NULL
        GROUP BY track_id
        ORDER BY artist_name ASC, track_name ASC
    """
    ).fetchall()
    conn.close()

    rows = [list(row) for row in result]

    sheet = Spreadsheet(LEVBOARD_SHEET)
    sheet.delete_range(f'MISSING_URIS!A2:D4500')
    sheet.update_range(f'MISSING_URIS!A2:D{len(rows) + 1}', rows)

    print(f'sent out {len(rows)} untied URIs to spreadsheet')


def delete_database(db_path: str) -> None:

    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        DELETE FROM listens;
        DELETE FROM sqlite_sequence WHERE name='listens';
    """
    )
    conn.close()
    print('database cleared')


def fill_missing_statsfm_ids(db_path: str) -> None:
    """
    fill in all missing stats fm ids with the spotify id.
    basically allows us to still process unbound songs.
    """

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        UPDATE listens SET statsfm_id = track_id WHERE statsfm_id IS NULL
    """
    )
    conn.commit()
    print(f'filled {conn.total_changes} rows with missing stats fm ids')
    conn.close()


def apply_daily_play_cap(db_path: str, cap: int = 25) -> None:
    """Delete listens beyond `cap` per track per calendar day."""

    fill_missing_statsfm_ids(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        DELETE FROM listens
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY statsfm_id, DATE(ts / 1000, 'unixepoch')
                           ORDER BY ts
                       ) AS rn
                FROM listens
            )
            WHERE rn <= ?
        )
    """,
        (cap,),
    )
    conn.commit()
    deleted = conn.total_changes
    conn.close()
    print(f'removed {deleted} listens over daily cap of {cap}')


def process_local_streams() -> None:
    json_files = sorted(Path('./raw').glob('Streaming_History_*.json'))

    if not json_files:
        print('no json files found in ./raw')
        sys.exit(1)

    delete_database(DB_PATH)
    print(f"processing {len(json_files)} file(s) into '{DB_PATH}' ...\n")
    ingest_files(DB_PATH, json_files)
    get_missing_songs(DB_PATH)
    apply_daily_play_cap(DB_PATH, 25)


if __name__ == '__main__':
    process_local_streams()
