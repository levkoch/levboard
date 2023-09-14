import yaml
from model import Credits


def display_artist_tags():
    with open('levboard/data/songs.yml', 'r+') as fp:
        data: dict[str, dict] = yaml.safe_load(fp)

    all_artists = [
        song_dict['artists']
        for song_dict in data.values()
        if isinstance(song_dict['artists'][0], dict)
    ]

    artist_tags: set = set()
    for artist_group in all_artists:
        for artist_dict in artist_group:
            artist_tag: str = artist_dict['name']
            if not artist_tag.startswith('XXX'):
                artist_tags.add(artist_tag)

    print(*artist_tags, sep='\n')


def try_to_parse_artists():
    with open('levboard/data/songs.yml', 'r+') as fp:
        data: dict[str, dict] = yaml.safe_load(fp)

    for song_dict in data.values():
        print(song_dict['artists'])
        credit = Credits(song_dict['artists'])
        print(str(credit))


def find_parsed_songs():
    with open('levboard/data/songs.yml', 'r') as fp:
        data: dict = yaml.safe_load(fp).values()

        for image_dict in data:
            print(image_dict)


try_to_parse_artists()
