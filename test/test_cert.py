'''
levboard/test/test_cert.py
Checking that our certification objects work correctly.
'''

import pytest

from ..main.model import AlbumCert, CertType, SongCert
from ..main.model.cert import AbstractCert


# comparison mechanism is in `BaseCert` so we only need
# to check one subtype and not both.
@pytest.mark.parametrize(
    ('cert1', 'cert2', 'expected'),
    [
        (600, 100, False),
        (100, 100, False),
        (110, 100, False),  # false because both are Gold
        (100, 600, True),
        (0, 200, True),
        (600, 1200, True),
        (3000, 4000, True),
        (0, 2000, True),
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
    assert expected == (
        SongCert.from_units(cert1) == SongCert.from_units(cert2)
    )


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
    tester = SongCert.from_units(units)
    assert (tester._cert, tester._mult) == (cert, mult)


@pytest.mark.parametrize(
    ('cert_type', 'mult', 'cert'),
    [(SongCert, 3, CertType.PLATINUM), (SongCert, 12, CertType.DIAMOND)],
)
def test_make_from_parts(cert_type: type[AbstractCert], mult: int, cert: CertType):
    tester = cert_type(mult, cert)
    assert (tester.mult, tester.cert) == (mult, cert)


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
    tester = AlbumCert.from_units(units)
    assert (tester._cert, tester._mult) == (cert, mult)


@pytest.mark.parametrize(
    ('units', 'cert_type', 'text'),
    [
        (0, SongCert, 'SongCert(0, CertType.NONE)'),
        (25, SongCert, 'SongCert(0, CertType.NONE)'),
        (300, SongCert, 'SongCert(0, CertType.PLATINUM)'),
        (1000, SongCert, 'SongCert(5, CertType.PLATINUM)'),
        (0, AlbumCert, 'AlbumCert(0, CertType.NONE)'),
        (600, AlbumCert, 'AlbumCert(0, CertType.GOLD)'),
        (2100, AlbumCert, 'AlbumCert(2, CertType.PLATINUM)'),
        (5000, AlbumCert, 'AlbumCert(5, CertType.PLATINUM)'),
    ],
)
def test_cert_from_units_str(units: int, cert_type: type[AbstractCert], text: str):
    tester = cert_type.from_units(units)
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
def test_cert_str(units: int, cert_type: type[AbstractCert], text: str):
    tester = cert_type.from_units(units)
    assert text == str(tester)


@pytest.mark.parametrize(
    ('cert', 'flag', 'text'),
    [
        (SongCert(0, CertType.NONE), '', '-'),
        (SongCert(0, CertType.NONE), 's', '-'),
        (SongCert(0, CertType.NONE), 'f', 'Un-Certified'),
        (SongCert(0, CertType.GOLD), '', '●'),
        (SongCert(0, CertType.GOLD), 's', '●'),
        (SongCert(0, CertType.GOLD), 'f', 'Gold'),
        (SongCert.from_units(200), '', '▲'),
        (SongCert.from_units(200), 's', '▲'),
        (SongCert.from_units(200), 'f', 'Platinum'),
        (SongCert.from_units(600), '', '3x▲'),
        (SongCert.from_units(600), 's', '3x▲'),
        (SongCert.from_units(600), 'f', '3 times Platinum'),
        (SongCert.from_units(2000), '', '10x⬥'),
        (SongCert.from_units(2000), 's', '10x⬥'),
        (SongCert.from_units(2000), 'S', '⬥'),
        (SongCert.from_units(2000), 'f', '10 times Diamond'),
        (SongCert.from_units(2000), 'F', 'Diamond'),
        (SongCert.from_units(2600), '', '13x⬥'),
        (SongCert.from_units(2600), 's', '13x⬥'),
        (SongCert.from_units(2600), 'S', '⬥ 3x▲'),
        (SongCert.from_units(2600), 'f', '13 times Diamond'),
        (SongCert.from_units(2600), 'F', 'Diamond and 3 times Platinum'),
    ],
)
def test_cert_format(cert, flag: str, text: str):
    assert format(cert, flag) == text


@pytest.mark.parametrize(
    ('cert', 'flag', 'text'),
    [
        (SongCert(0, CertType.GOLD), '>2', ' ●'),
        (SongCert(0, CertType.GOLD), '<2', '● '),
        (SongCert(0, CertType.GOLD), '^3', ' ● '),
    ],
)
def test_cert_align(cert, flag: str, text: str):
    assert format(cert, flag) == text


@pytest.mark.parametrize(
    ('cert', 'flag', 'text'),
    [
        (SongCert(0, CertType.GOLD), '>2s', ' ●'),
        (SongCert(0, CertType.GOLD), '<2s', '● '),
        (SongCert(0, CertType.GOLD), '^3s', ' ● '),
        (SongCert(0, CertType.GOLD), '<6f', 'Gold  '),
        (SongCert(0, CertType.GOLD), '>6f', '  Gold'),
        (SongCert(0, CertType.GOLD), '^6f', ' Gold '),
        (SongCert(11, CertType.DIAMOND), '^5S', ' ⬥ ▲ '),
        (SongCert(12, CertType.DIAMOND), '>7S', '  ⬥ 2x▲'),
    ],
)
def test_cert_align_with_flags(cert: SongCert, flag: str, text: str):
    assert format(cert, flag) == text


def test_cant_make_basecert():
    with pytest.raises(TypeError):
        AbstractCert(200)


@pytest.mark.parametrize(
    ('cert_type'),
    [
        (AlbumCert),
        (SongCert),
    ],
)
def test_make_default_cert(cert_type: type[AbstractCert]):
    default = cert_type()

    assert (default.cert, default.mult) == (CertType.NONE, 0)

@pytest.mark.parametrize(
    ('cert_type'),
    [
        (AlbumCert),
        (SongCert),
    ],
)
def test_cert_is_hashable(cert_type: type[AbstractCert]):
    certs = {
        cert_type(0, CertType.GOLD),
        cert_type(2, CertType.PLATINUM),
        cert_type(2, CertType.PLATINUM),
    }
    assert len(certs) == 2 # two of the same
