import pytest
from ..levboard.src.model import Credits, Artist, Band


@pytest.mark.parametrize(
    ('constructor', 'expected'),
    [
        ((('25059 Ariana Grande', 'main'),), 'Ariana Grande'),
        (
            (
                ('25059 Ariana Grande', 'main'),
                ('11619 Nicki Minaj', 'feature'),
            ),
            'Ariana Grande ft. Nicki Minaj',
        ),
        (
            (('2089 Dua Lipa', 'main'), ('124584 BLACKPINK', 'lead')),
            'Dua Lipa with BLACKPINK',
        ),
        (
            (
                ('11619 Nicki Minaj', 'main'),
                ('354 Labrinth', 'lead'),
                ('443 Eminem', 'feature'),
            ),
            'Nicki Minaj with Labrinth ft. Eminem',
        ),
        (
            (
                ('355 Charli XCX', 'main'),
                ('441 Kim Petras', 'feature'),
                ('112 Jay Park', 'feature'),
            ),
            'Charli XCX ft. Jay Park & Kim Petras',
        ),
        (
            (
                ('11619 Nicki Minaj', 'main'),
                ('1342 Drake', 'feature'),
                ('1786 Lil Wayne', 'feature'),
                ('448 Chris Brown', 'feature'),
            ),
            'Nicki Minaj ft. Chris Brown, Drake & Lil Wayne',
        ),
        (
            (
                ('4423 J Baldvin', 'main'),
                ('2089 Dua Lipa', 'lead'),
                ('228 Bad Bunny', 'lead'),
                ('2755 Tainy', 'lead'),
            ),
            'J Baldvin with Bad Bunny, Dua Lipa & Tainy',
        ),
    ],
)
def test_str_credits(constructor: tuple, expected: str):
    assert str(Credits(constructor)) == expected


@pytest.mark.parametrize(
    ('constructor', 'expected'),
    [
        (('Ariana Grande',), 'Ariana Grande'),
        (
            ('Ariana Grande', 'Nicki Minaj'),
            'Ariana Grande ft. Nicki Minaj',
        ),
        (
            ('Lady Gaga', 'Charli XCX', 'A. G. Cook'),
            'Lady Gaga ft. A. G. Cook & Charli XCX',
        ),
    ],
)
def test_str_untagged_credits(constructor: tuple, expected: str):
    assert str(Credits(constructor)) == expected


@pytest.mark.parametrize(
    ('constructor', 'expected'),
    [
        (
            (
                ('203847 Ashley O', 'main'),
                ('11 Miley Cyrus', 'member', 'Ashley O'),
            ),
            'Ashley O (Miley Cyrus)',
        ),
        (
            (
                ('4448 Maroon 5', 'main'),
                ('438 Adam Levine', 'member', 'Maroon 5'),
                ('257 SZA', 'feature'),
            ),
            'Maroon 5 (Adam Levine) ft. SZA',
        ),
        (
            (
                ('338 Young Money', 'main'),
                ('858484 Nicki Minaj', 'member', 'Young Money'),
                ('447 Tyga', 'member', 'Young Money'),
                ('23848 Lil Wayne', 'member', 'Young Money'),
            ),
            'Young Money (Lil Wayne, Nicki Minaj & Tyga)',
        ),
    ],
)
def test_band_members_credits(constructor, expected):
    assert str(Credits(constructor)) == expected


@pytest.mark.parametrize(
    ('constructor',),
    [
        ((('25059 Ariana Grande', 'main'),),),
        ((('2089 Dua Lipa', 'main'), ('124584 BLACKPINK', 'lead')),),
        (
            (
                ('25059 Ariana Grande', 'main'),
                ('11619 Nicki Minaj', 'feature'),
            ),
        ),
        (
            (
                ('11619 Nicki Minaj', 'main'),
                ('354 Labrinth', 'lead'),
                ('443 Eminem', 'feature'),
            ),
        ),
        (
            (
                ('332 Charli XCX', 'main'),
                ('441 Kim Petras', 'feature'),
                ('112 Jay Park', 'feature'),
            ),
        ),
        (
            (
                ('11619 Nicki Minaj', 'main'),
                ('1342 Drake', 'feature'),
                ('2184 Lil Wayne', 'feature'),
                ('448 Chris Brown', 'feature'),
            ),
        ),
        (
            (
                ('4423 J Baldvin', 'main'),
                ('2089 Dua Lipa', 'lead'),
                ('228 Bad Bunny', 'lead'),
                ('2755 Tainy', 'lead'),
            ),
        ),
        (
            (
                ('203847 Ashley O', 'main'),
                ('11 Miley Cyrus', 'member', 'Ashley O'),
            ),
        ),
        (
            (
                ('4448 Maroon 5', 'main'),
                ('438 Adam Levine', 'member', 'Maroon 5'),
                ('257 SZA', 'feature'),
            ),
        ),
        (
            (
                ('338 Young Money', 'main'),
                ('858484 Nicki Minaj', 'member', 'Young Money'),
                ('447 Tyga', 'member', 'Young Money'),
                ('23848 Lil Wayne', 'member', 'Young Money'),
            ),
        ),
    ],
)
def test_members_in_credits(constructor: tuple[tuple, ...]):
    credits = Credits(constructor)
    artists = (
        Artist(tag.split()[0], ' '.join(tag.split()[1:]))
        for tag in (row[0] for row in constructor)
    )

    for artist in artists:
        assert artist in credits


@pytest.mark.parametrize(
    ('constructor',),
    [
        (
            [
                {
                    'name': '25059 Ariana Grande',
                    'type': 'main',
                },
            ],
        ),
        (
            [
                {'name': '2089 Dua Lipa', 'type': 'main'},
                {'name': '124584 BLACKPINK', 'type': 'lead'},
            ],
        ),
        (
            [
                {'name': '11619 Nicki Minaj', 'type': 'main'},
                {'name': '354 Labrinth', 'type': 'lead'},
                {'name': '443 Eminem', 'type': 'feature'},
            ],
        ),
        (
            [
                {'name': '338 Young Money', 'type': 'main'},
                {
                    'name': '858484 Nicki Minaj',
                    'type': 'member',
                    'band': 'Young Money',
                },
                {'name': '447 Tyga', 'type': 'member', 'band': 'Young Money'},
                {
                    'name': '23848 Lil Wayne',
                    'type': 'member',
                    'band': 'Young Money',
                },
            ],
        ),
    ],
)
def test_credit_serialization(constructor: tuple[dict, ...]):
    serialized = Credits(constructor).to_list()
    for credit_line in constructor:
        assert credit_line in serialized
