from collections.abc import Mapping
from enum import Enum
from typing import Iterable, Iterator, Optional, TypedDict, Union


class CreditType(Enum):
    """
    All of the different credit types people can recieve for a song.
    Includes any main credits along with any additional credits.
    """

    # main credits
    MAIN = 'main'
    LEAD = 'lead'
    FEATURE = 'feature'

    # special tag
    MEMBER = 'member'

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
    __slots__ = ('tag', 'name')

    def __init__(self, tag: str, name: str):
        self.tag: str = tag
        self.name: str = name

    def __str__(self):
        return self.name

    def to_html(self):
        return f'<a href="https://stats.fm/artist/{self.tag}">{self.name}</a>'

    def __eq__(self, other):
        return (self.tag == other.tag) and (
            self.name == other.name
        )

    def __hash__(self):
        return hash((self.tag, self.name))


class Band(Artist):
    __slots__ = ('members',)

    def __init__(self, tag: str, name: str):
        super().__init__(tag, name)
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


CreditField = TypedDict('CreditField', artist=str, type=CreditType, band=str)
CreditTuple = tuple[str, Union[str, CreditType], Optional[str]]


class Credits:
    """
    A class representing the credits on a song.
    Can be created using either a list of credit field dictionaries,
    a list of credit field tuples, or a list of artist name strings.

    ```python
    >>> Credits(["Ariana Grande", "Nicki Minaj"])
    "Ariana Grande ft. Nicki Minaj"
    >>> Credits([("123 Ariana Grande", "main"), ("448 Social House", "lead")])
    "Ariana Grande with Social House"
    >>> Credits([
            {'name': '165 Silk City', 'type': 'main'},
            {'name': '208 Dua Lipa', 'type': 'lead'},
            {'name': '474 Diplo', 'type': 'member', 'band': 'Silk City'},
            {'name': '116 Mark Ronson', 'type': 'member', 'band': 'Silk City'}
        ])
    "Silk City (Diplo, Mark Ronson) with Dua Lipa"
    >>> Credits([("484 Ashley O", "main"), ("223 Miley Cyrus", "member", "Ashley O")])
    "Ashley O (Miley Cyrus)"
    ```
    """

    def __init__(
        self,
        info: Union[
            Iterable[CreditField], Iterable[CreditTuple], Iterable[str]
        ],
    ):
        self.credits: set[tuple[Artist, CreditType]] = set()
        info = self._sanitize_info(list(info))
        self._attach_credits(info)

    def _sanitize_info(
        self,
        info: Union[
            Iterable[CreditField], Iterable[CreditTuple], Iterable[str]
        ],
    ) -> list[CreditField]:
        """
        Converts the info passed into the credits to be manageable. Makes
        it into a list of dictionaries that have the required fields to
        be added in.
        """

        first = info[0]

        # we got an untagged list of artists, so we hope that the first
        # one was the main artist and the rest were features.
        # works great for solo songs.
        if isinstance(first, str):
            new_info = [
                {'name': Artist('XXX', first), 'type': CreditType.MAIN}
            ]
            if len(info) > 1:
                new_info.extend(
                    {'name': Artist('XXX', artist), 'type': CreditType.FEATURE}
                    for artist in info[1:]
                )
            return new_info

        # we got a list of mappings, so we create tuples out of the dicts and
        # parse the tuples later.
        if isinstance(first, Mapping):
            info = [
                (credit['name'], 'member', credit['band'])
                if credit['type'] == 'member'
                else (credit['name'], credit['type'])
                for credit in info
            ]

        new_info = []
        # we got tuples of information either of the form
        # ("XXX Artist", "credit") or ("XXX Artist", "member", "band name")
        for credit_tuple in info:
            artist_tag = credit_tuple[0]
            credit_type = credit_tuple[1]

            artist = Artist(
                artist_tag.split()[0], ' '.join(artist_tag.split()[1:])
            )
            credit = CREDIT_CONVERSION[credit_type]
            credit_dict = {'name': artist, 'type': credit}

            if credit is CreditType.MEMBER:
                credit_dict['band'] = credit_tuple[2]

            new_info.append(credit_dict)

        return new_info

    def _attach_credits(self, info: Iterable[CreditField]):
        """
        Attaches any credits into the credits, adding in any
        solo artists and binding members to their groups.
        """

        solo_artists = (
            artist for artist in info if artist['type'] != CreditType.MEMBER
        )
        for credit_dict in solo_artists:
            self.credits.add((credit_dict['name'], credit_dict['type']))

        members = (
            artist for artist in info if artist['type'] == CreditType.MEMBER
        )

        for credit_dict in members:
            # credited as a member of a group
            band, credit = next(
                (b, c)
                for (b, c) in self.credits
                if b.name == credit_dict['band']
            )
            if not hasattr(band, 'add_artist'):
                # check if a band instance hasn't already been
                # created for the band.
                band = Band(band.tag, band.name)
                # adding it in again will overwrite the original
                # Artist instance that used to represent the band.
                self.credits.remove((band, credit))
                self.credits.add((band, credit))

            band.add_artist(credit_dict['name'])

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

    def to_list(self) -> list[dict]:
        info = []
        for artist, credit in self.credits:
            if hasattr(artist, 'add_artist'):
                artist: Band
                for member in artist.members:
                    info.append(
                        {
                            'name': f'{member.tag} {member.name}',
                            'type': 'member',
                            'band': artist.name,
                        }
                    )

            info.append(
                {
                    'name': f'{artist.tag} {artist.name}',
                    'type': credit.value,
                }
            )

        return info
