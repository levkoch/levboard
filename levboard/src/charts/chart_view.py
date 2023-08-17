from datetime import date

from ..storage import Process


def get_chart_week(process: Process, week_count: int) -> dict:
    chart_date = date.fromisoformat('2023-08-15')
    chart_lines = [
        [
            '=',
            'What Was I Made For?',
            'Billie Eilish',
            1,
            1,
            5,
            434,
            25,
            '1\u2075',
            115,
        ],
        [
            '\u25b249',
            'better off',
            'Ariana Grande',
            2,
            51,
            6,
            232,
            22,
            '2',
            115,
        ],
        [
            '\u25b24',
            "Halley's Comet",
            'Billie Eilish',
            3,
            7,
            28,
            142,
            10,
            '2\u00b2',
            115,
        ],
        ['\u25b22', 'my future', 'Billie Eilish', 4, 6, 27, 140, 10, '4', 115],
        [
            '\u25b24',
            "when the party's over",
            'Billie Eilish',
            4,
            8,
            18,
            140,
            10,
            '4',
            115,
        ],
        [
            '\u25bc1',
            'Getting Older',
            'Billie Eilish',
            6,
            5,
            17,
            136,
            9,
            '4',
            115,
        ],
        ['\u25b21', 'Bored', 'Billie Eilish', 7, 8, 9, 122, 8, '2', 115],
        ['\u25b23', 'Oxytocin', 'Billie Eilish', 8, 11, 15, 118, 9, '8', 115],
        ['\u25b213', 'my hair', 'Ariana Grande', 9, 22, 71, 116, 9, '1', 115],
        [
            '\u25bc6',
            'ocean eyes',
            'Billie Eilish with blackbear',
            9,
            3,
            63,
            116,
            7,
            '1\u00b3',
            115,
        ],
    ]
    return {
        'week': {'count': week_count, 'date': '2023-08-15'},
        'entries': (
            {
                'movement': line[0],
                'image': 'https://i.scdn.co/image/ab67616d0000b2737b688587a6754481c53f6bb7',
                'title': line[1],
                'artists': line[2],
                'place': line[3],
                'previous': line[4],
                'weeks': line[5],
                'points': line[6],
                'peak': line[8],
            }
            for line in chart_lines
        ),
    }
