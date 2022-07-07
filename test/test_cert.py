import pytest

from ..main.model import CertType, SongCert, AlbumCert

# comparison mechanism is in `BaseCert` so we only need 
# to check one subtype and not both.
@pytest.mark.parametrize(
    ('cert1', 'cert2', 'expected'),
    [
        (600, 100, False),
        (100, 100, False),
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
