from enum import Enum
from typing import Iterable, Iterator, Optional, Union


class CreditType(Enum):
    """
    All of the different credit types people can recieve for a song.
    Includes any main credits along with any additional credits.
    """

    # main credits
    MAIN = 'main'
    LEAD = 'lead'
    FEATURE = 'feature'

    # additional credits
    PRODUCER = 'producer'
    COPRODUCER = 'co-producer'
    VOCALIST = 'vocalist'
    WRITER = 'writer'


CREDIT_CONVERSION = {element.value: element for element in CreditType}


def combine_artists(iter: Iterable[str]) -> str:
    artists = list(sorted(iter))
    if len(artists) == 1:
        return artists[0]
    if len(artists) == 2:
        return ' & '.join(artists)
    return f'{", ".join(artists[:-2])}, {" & ".join(artists[-2:])}'


class Artist:
    __slots__ = ('artist_id', 'name')

    def __init__(self, artist_id: str, name: str):
        self.artist_id: str = artist_id
        self.name: str = name

    def __str__(self):
        return self.name

    def to_html(self):
        return f'<a href="https://stats.fm/artist/{self.artist_id}">{self.name}</a>'

    def __eq__(self, other):
        return (self.artist_id == other.artist_id) and (
            self.name == other.name
        )

    def __hash__(self):
        return hash((self.artist_id, self.name))


class Band(Artist):
    __slots__ = ('members',)

    def __init__(self, artist_id: str, name: str):
        super().__init__(artist_id, name)
        self.members: set[Artist] = set()

    def add_artist(self, artist: Artist):
        self.members.add(artist)

    def __str__(self):
        return f'{super().__str__()} ({combine_artists(str(m) for m in self.members)})'

    def to_html(self):
        return (
            f'{super().to_html()}'
            f' ({combine_artists(member.to_html() for member in self.members)})'
        )


class Credits:
    def __init__(
        self,
        info: Iterable[tuple[str, Union[str, CreditType], Optional[str]]],
    ):
        self.credits: set[tuple[Artist, CreditType]] = set()
        self._attach_credits(info)

    def _attach_credits(self, info: Iterable):
        for credit_tuple in info:
            artist_tag = credit_tuple[0]
            credit_type = credit_tuple[1]

            artist = Artist(
                artist_tag.split()[0], ' '.join(artist_tag.split()[1:])
            )
            print(f'created {artist}')

            if credit_type == 'member':
                # credited as a member of a group
                band, credit = next(
                    (b, c)
                    for (b, c) in self.credits
                    if b.name == credit_tuple[2]
                )
                if not hasattr(band, 'add_artist'):
                    band = Band(band.artist_id, band.name)
                    print(f'creating band {band}')
                    self.credits.remove((band, credit))
                    self.credits.add((band, credit))
                    # adding it in again will overwrite the original
                    # Artist instance that used to represent the band.

                band.add_artist(artist)
                print(f'added {artist} into {band}')
                print(
                    f'band members: {combine_artists(str(m) for m in band.members)}'
                )

            else:
                # credited as an individual
                try:
                    self.credits.add((artist, CREDIT_CONVERSION[credit_type]))
                except IndexError:
                    raise ValueError('unsupported credit type')
                print(f'added {artist} into credits')

    def __iter__(self) -> Iterator[Artist]:
        for (artist, _) in self.credits:
            yield artist
            if isinstance(artist, Band):
                yield from artist.members

    def __str__(self) -> str:
        """
        Comps together all of the artists to create a credit line.
        """

        credit_str = ''
        main_artist = next(
            a for (a, c) in self.credits if c == CreditType.MAIN
        )
        credit_str += str(main_artist)
        if len(self.credits) == 1:
            return credit_str

        co_lead_artists = [
            a for (a, c) in self.credits if c == CreditType.LEAD
        ]

        if co_lead_artists:
            credit_str += ' with '
            credit_str += combine_artists(str(a) for a in co_lead_artists)

        feature_artists = [
            a for (a, c) in self.credits if c == CreditType.FEATURE
        ]

        if feature_artists:
            credit_str += ' ft. '
            credit_str += combine_artists(str(a) for a in feature_artists)

        return credit_str

    def to_html(self) -> str:
        """
        Comps together all of the artists into html to display their pages.
        """

        html_str = '<p>'
        main_artist = next(
            a for (a, c) in self.credits if c == CreditType.MAIN
        )
        html_str += main_artist.to_html()
        if len(self.credits) == 1:
            return html_str + '</p>'

        co_lead_artists = [
            a.to_html() for (a, c) in self.credits if c == CreditType.LEAD
        ]

        if co_lead_artists:
            html_str += ' with '
            html_str += combine_artists(co_lead_artists)

        feature_artists = [
            a.to_html() for (a, c) in self.credits if c == CreditType.FEATURE
        ]

        if feature_artists:
            html_str += ' ft. '
            html_str += combine_artists(feature_artists)

        return html_str + '</p>'
