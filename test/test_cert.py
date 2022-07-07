import pytest

from ..main.model import CertType, SongCert, AlbumCert

# comparison mechanism is in `BaseCert` so we only need
# to check one subtype and not both.
@pytest.mark.parametrize(
    ('cert1', 'cert2', 'expected'),
    [
        (600, 100, False),
        (100, 100, False),
        (110, 100, False), # true because both are Gold
        (100, 600, True),
        (0, 200, False),
        (600, 1200, True),
        (3000, 4000, True),
        (0, 2000, False),
        (100, 2000, True),
        (2000, 0, False),
        (2000, 100, False),
        (2000, 600, False),
    ],
)
def test_cert_comparison(cert1: int, cert2: int, expected: bool):
    assert expected == (SongCert(cert1) < SongCert(cert2))


# so is equality testing
@pytest.mark.parametrize(
    ('cert1', 'cert2', 'expected'),
    [(100, 100, True), (150, 100, True), (700, 600, True), (0, 200, False)],
)
def test_cert_equality(cert1: int, cert2: int, expected: bool):
    assert expected == (SongCert(cert1) == SongCert(cert2))


@pytest.mark.parametrize(
    ('units', 'cert', 'mult'),
    [
        (2200, CertType.DIAMOND, 11),
        (600, CertType.PLATINUM, 3),
        (200, CertType.PLATINUM, 0),
        (100, CertType.GOLD, 0),
        (30, CertType.NONE, 0),
    ],
)
def test_songcert_creation(units: int, cert: CertType, mult: int):
    tester = SongCert(units)
    assert (tester._cert, tester._mult) == (cert, mult)


@pytest.mark.parametrize(
    ('units', 'cert', 'mult'),
    [
        (11000, CertType.DIAMOND, 11),
        (3000, CertType.PLATINUM, 3),
        (1000, CertType.PLATINUM, 0),
        (500, CertType.GOLD, 0),
        (100, CertType.NONE, 0),
    ],
)
def test_albumcert_creation(units: int, cert: CertType, mult: int):
    tester = AlbumCert(units)
    assert (tester._cert, tester._mult) == (cert, mult)


@pytest.mark.parametrize(
    ('units', 'cert_type', 'text'),
    [
        (0, SongCert, 'SongCert(0)'),
        (25, SongCert, 'SongCert(25)'),
        (300, SongCert, 'SongCert(300)'),
        (1000, SongCert, 'SongCert(1000)'),
        (0, AlbumCert, 'AlbumCert(0)'),
        (600, AlbumCert, 'AlbumCert(600)'),
        (2100, AlbumCert, 'AlbumCert(2100)'),
        (5000, AlbumCert, 'AlbumCert(5000)'),
    ],
)
def test_cert_repr(units: int, cert_type: type, text: str):
    tester = cert_type(units)
    assert text == repr(tester)


@pytest.mark.parametrize(
    ('units', 'cert_type', 'text'),
    [
        (0, SongCert, '-'),
        (100, SongCert, '●'),
        (200, SongCert, '▲'),
        (400, SongCert, '2x▲'),
        (2000, SongCert, '10x⬥'),
        (3600, SongCert, '18x⬥'),
        (0, AlbumCert, '-'),
        (500, AlbumCert, '●'),
        (1000, AlbumCert, '▲'),
        (2000, AlbumCert, '2x▲'),
        (10000, AlbumCert, '10x⬥'),
        (18000, AlbumCert, '18x⬥'),
    ],
)
def test_cert_str(units: int, cert_type: type, text: str):
    tester = cert_type(units)
    assert text == str(tester)


@pytest.mark.parametrize(
    ('cert', 'flag', 'text'),
    [
        (SongCert(0), '', '-'),
        (SongCert(0), 's', '-'),
        (SongCert(0), 'f', 'Un-Certified'),
        (SongCert(100), '', '●'),
        (SongCert(100), 's', '●'),
        (SongCert(100), 'f', 'Gold'),
        (SongCert(200), '', '▲'),
        (SongCert(200), 's', '▲'),
        (SongCert(200), 'f', 'Platinum'),
        (SongCert(600), '', '3x▲'),
        (SongCert(600), 's', '3x▲'),
        (SongCert(600), 'f', '3 times Platinum'),
        (SongCert(2000), '', '10x⬥'),
        (SongCert(2000), 's', '10x⬥'),
        (SongCert(2000), 'S', '⬥'),
        (SongCert(2000), 'f', '10 times Diamond'),
        (SongCert(2000), 'F', 'Diamond'),
        (SongCert(2600), '', '13x⬥'),
        (SongCert(2600), 's', '13x⬥'),
        (SongCert(2600), 'S', '⬥ 3x▲'),
        (SongCert(2600), 'f', '13 times Diamond'),
        (SongCert(2600), 'F', 'Diamond and 3 times Platinum'),
    ],
)
def test_cert_format(cert, flag: str, text: str):
    assert format(cert, flag) == text
