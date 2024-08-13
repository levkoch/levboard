"""functions for the raspberry pi until i figure out what i'll actaully be doing with it."""

import json

from config import COLLECTION_SHEET, LEVBOARD_SHEET, RECORDS_FILE
from spreadsheet import Spreadsheet


def update_records_info():
    collection = Spreadsheet(COLLECTION_SHEET)
    levboard = Spreadsheet(LEVBOARD_SHEET)

    albums_info: dict[str, dict[str, str]] = {}
    for row in levboard.get_range("'Top Albums'!A2:J").get('values'):
        (
            place,
            album,
            _,  # C artist
            _,  # D year
            units,
            _,  # F certification
            plays,
            points,
            weeks,
            peak,
        ) = row
        albums_info[album] = {
            'place': int(place.replace(',', '')),
            'units': int(units.replace(',', '')),
            'plays': int(plays.replace(',', '')),
            'points': int(points.replace(',', '')),
            # the weeks are the one item that shows as "-" when it's 0,
            # so we have to convert that into an numeric value
            'weeks': int(weeks.replace(',', '').replace('-', '0')),
            'peak': peak,
        }

    songs_info = {}
    for row in levboard.get_range("'All Time'!A3:P").get('values'):
        (
            song,
            _,  # B artist
            points,
            place,
            _,  # E sheet id
            _,  # F #1 weeks
            _,  # G top 3 weeks
            _,  # H top 5 weeks
            _,  # I top 10 weeks
            _,  # J top 20 weeks
            _,  # K top 30 weeks
            weeks,
            peak,
            _,  # N chart plays
            plays,
            units,
        ) = row
        # since the all time sheet fills in blank values when there isn't a
        # song specified, we skip all the ones without a song specified
        if not song:
            continue
        songs_info[song] = {
            'place': int(place.replace(',', '')),
            'units': int(units.replace(',', '')),
            'plays': int(plays.replace(',', '')),
            'points': int(points.replace(',', '')),
            # the weeks are the one item that shows as "-" when it's 0,
            # so we have to convert that into an numeric value
            'weeks': int(weeks.replace(',', '').replace('-', '0')),
            'peak': peak,
        }

    records = {}
    for row in collection.get_range('COLLECTION!A2:K').get('values'):
        (
            rfid,
            artist,
            title,
            format,
            details,
            speed,
            year,
            levboard_type,
            levboard_title,
            discogs,
            upc,
        ) = row
        levboard_info: dict[str, str] = {
            'type': levboard_type,
            'title': levboard_title,
        }
        # albums without a levboard equivalent (like compilations and 
        # singles that i bought physical copies of but that didn't chart)
        # are registered as "NONE"
        if levboard_title != 'NONE':
            info_pool = albums_info if levboard_type == 'Album' else songs_info
            info_field = info_pool.get(levboard_title)
            if info_field is None: # no match so it was merged wrong
                print(f'Unable to find levboard item named {levboard_title}')
            else:
                levboard_info.update(info_field)

        records[rfid] = {
            'rfid': rfid,
            'artist': artist,
            'title': title,
            'format': format,
            'details': details,
            'speed': speed,
            'year': year,
            'discogs': discogs,
            'upc': upc,
            'levboard': levboard_info,
        }

    with open(RECORDS_FILE, 'w', encoding='UTF-8') as f:
        json.dump(records, f, indent=4)


if __name__ == '__main__':
    update_records_info()
