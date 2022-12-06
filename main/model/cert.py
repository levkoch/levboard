"""
levboard/main/model/cert.py

Where all of the certifications are held. Certifications hold information
on the units that a musical entity has in a more helpful form.

Classes:
* CertType: An Enum with the four different certificaiton types.
* SongCert: A certification for a song.
* AlbumCert: A certification for an album.

Abstract Classes:
* AbstractCert: A certification that doesn't support constructing from units.
    The base class of both SongCert and AlbumCert.
"""

import operator
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Any
from pydantic import NonNegativeInt


class CertType(Enum):
    """
    The four different certification types.

    Attributes:
    * `NONE`: Music unit is not certified. Maps to `"Un-Certified"` or `""`.
    * `GOLD`: Music unit is certified Gold. Maps to `"Gold"` or `"●"`.
    * `PLATINUM`: Music unit is certified Platinum or higher. Maps to
        `"Platinum"` or `"▲"`.
    * `DIAMOND`: Music unit is certified 10x multi-Platinum or higher.
        Maps to `"Diamond"` or `"⬥"`.
    """

    NONE = 'Un-Certified'
    GOLD = 'Gold'
    PLATINUM = 'Platinum'
    DIAMOND = 'Diamond'

    def to_symbol(self) -> str:
        """
        Returns the certification as a symbol, as denoted in the main
        docstring, for shorthand use.
        """

        convert = {
            CertType.NONE: '-',
            CertType.GOLD: '●',
            CertType.PLATINUM: '▲',
            CertType.DIAMOND: '⬥',
        }
        return convert[self]


def _cmp(operate) -> Callable[['AbstractCert', Any], bool]:
    """Factory function to make comparison attributes."""

    def comparer(instance, other) -> bool:
        try:
            return operate(instance.valcode, other.valcode)
        except AttributeError:
            return NotImplemented

    return comparer


class AbstractCert(ABC):
    """
    Base certification. Do NOT construct.

    Abstract Methods:
    * from_units: an alternate constructor that makes a cert from a unit amount.
    """

    __slots__ = ('_cert', '_mult')

    _cert: CertType
    _mult: NonNegativeInt

    def __init__(
        self, mult: NonNegativeInt = 0, cert: CertType = CertType.NONE
    ):
        if mult < 0:
            raise ValueError(
                'Multiplier / Units need to be a nonnegative int.'
            )
        self._mult = int(mult)
        self._cert = cert

    @classmethod
    @abstractmethod
    def from_units(cls, units: NonNegativeInt) -> 'AbstractCert':
        """
        Abstract Method - Loads the multiplier and cert type of the cert
        based on the units.
        """

        raise NotImplementedError(
            'Cannot instantiate an instance of `AbstractCert`. '
            'Use a subclass instead.'
        )

    @classmethod
    def from_symbol(cls, info: str) -> 'AbstractCert':
        if len(info) == 1:
            return cls.from_symbol('0x' + info)

        items = info.split('x')

        if len(items) == 0:
            mult, cert_letter = 0, 'N'

        elif len(items) == 1:
            if items[0].isnumeric():
                mult, cert_letter = int(items[0]), 'N'
            else:
                mult, cert_letter = 0, items[0]

        else:
            mult, cert_letter = items

        letter_to_cert_type = {
            'N': CertType.NONE,
            '-': CertType.NONE,
            'G': CertType.GOLD,
            '●': CertType.GOLD,
            'P': CertType.PLATINUM,
            '▲': CertType.PLATINUM,
            'D': CertType.DIAMOND,
            '⬥': CertType.DIAMOND,
        }

        return cls(int(mult), letter_to_cert_type[cert_letter.upper()])

    @property
    def mult(self) -> int:
        """
        mult (`int`): The multiplier of the certification. A non negative int.
        """
        return self._mult

    @property
    def cert(self) -> CertType:
        """
        cert (`CertType`): The certification type of the certification.
        A `cert.CertType` enum object.
        """
        return self._cert

    def __str__(self) -> str:
        if self._mult == 0:
            return self._cert.to_symbol()
        return f'{self._mult}x{self._cert.to_symbol()}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.mult!r}, {self.cert!s})'

    def __format__(self, fmt: str) -> str:
        # flags are '', 's', 'S', 'f', and 'F'

        if not fmt or fmt == 's':
            return str(self)

        if fmt[-1] not in ('s', 'S', 'f', 'F'):
            return format(str(self), fmt)

        if len(fmt) != 1:
            return format(format(self, fmt[-1]), fmt[:-1])

        if fmt == 'S':
            if self._cert != CertType.DIAMOND:
                return str(self)

            info = format(self, 'F')
            for (value, symbol) in (
                (i.value, i.to_symbol()) for i in CertType
            ):
                info = info.replace(value, symbol)
            info = info.replace(' times ', 'x')
            return info.replace(' and ', ' ')

        if fmt in ('f', 'F'):
            # if is certified GOLD or NONE
            if self._mult == 0:
                return self._cert.value

            # full form or when expanded full form is same as full form
            if fmt == 'f' or self._cert != CertType.DIAMOND:
                return f'{self._mult} times {self._cert.value}'

            # if they wanted the expanded full form
            # (which only impacts Diamond+ songs)

            diamond = self._mult // 10
            plat = self._mult % 10

            diamond_part = (
                f'{diamond} times Diamond' if diamond > 1 else 'Diamond'
            )
            if plat > 1:
                plat_part = f' and {plat} times Platinum'
            elif plat == 1:
                plat_part = ' Platinum'
            else:
                plat_part = ''

            return diamond_part + plat_part

        return NotImplemented

    @property
    def valcode(self) -> int:
        """
        valcode (`int`): Represents the certification as an integer. Internal
        property to make comparison easier. `0` is uncertified, `1` is Gold,
        and `2` or more is certified Platinum or higher, depending on how
        many times platinum.
        """

        code_map = {
            CertType.NONE: 0,
            CertType.GOLD: 1,
            CertType.PLATINUM: 2,
            CertType.DIAMOND: 2,
        }
        return code_map[self._cert] + self._mult

    __lt__ = _cmp(operator.lt)
    __le__ = _cmp(operator.le)
    __gt__ = _cmp(operator.gt)
    __ge__ = _cmp(operator.ge)
    __eq__ = _cmp(operator.eq)

    def __hash__(self) -> int:
        return hash((self.mult, self.cert))


class SongCert(AbstractCert):
    """
    Represents an song certification.

    Arguments:
    * units (`NonNegativeInt`): The units the song has. Should be `0` or greater.

    Attributes:
    * _units (`NonNegativeInt`): The amount of song units the represented by the
        certification. Should be `0` or greater.
    * _cert (`CertType`): The certification of the song. Does not include the
        multiplier, if applicable.
    * _mult (`NonNegetiveInt`): The multiplier for the certification. Will be `0`
        if the song is certified `GOLD`, `NONE`, or a single `PLATINUM`. Otherwise,
        it will be `2` - `9` for multi-`PLATINUM` and `11` or greater for `DIAMOND`.
    * __str__ (`str`): The certification as a string, in "mult (if has one) x
        cert symbol" form.

    Formatting flags:
    * `''`: (blank) Returns the same thing as calling `str(songcert)` on the songcert.
    * `'s'`: (symbol) The same as the blank call, with normal symbols. Will not split
        11x Diamond into 1x Diamond and 1x Platinum
    * `'S'`: (expanded symbol) Returns the certification as symbols, with diamond
        certification expanded into diamond and platinum.
    * `'f'`: (full) The certification with the full words instead of symbols.
    * `'F'`: (expanded full) The certification with the full words and diamond expanded.

    Additionally supports sorting, formatting and equality comparison.
    """

    __slots__ = ()

    @classmethod
    def from_units(cls, units: NonNegativeInt) -> 'SongCert':
        """
        Constructs a SongCert from units. Returns a new SongCert object.
        """

        mult = 0
        if units < 100:
            cert = CertType.NONE
        elif units < 200:
            cert = CertType.GOLD
        elif units < 2000:
            if units >= 400:
                mult = units // 200
            cert = CertType.PLATINUM
        else:
            mult = units // 200
            cert = CertType.DIAMOND

        return cls(mult, cert)

    def to_units(self) -> int:
        """Returns the certification as the units it represents."""

        if self.cert in (CertType.PLATINUM, CertType.DIAMOND):
            return self._mult * 200

        if self.cert is CertType.GOLD:
            return 100

        return 0


class AlbumCert(AbstractCert):
    """
    Represents an album certification.

    Arguments:
    * units (`NonNegativeInt`): The units the album has. Should be `0` or
        greater.

    Attributes:
    * _units (`NonNegativeInt`): The amount of units the represented
        by the certification. Should be `0` or greater.
    * _cert (`CertType`): The certification of the album. Does not include
        the multiplier, if applicable.
    * _mult (`NonNegetiveInt`): The multiplier for the certification. Will
        be `0` if the album is certified `GOLD`, `NONE`, or a single
        `PLATINUM`. Otherwise, it will be `2` - `9` for multi-`PLATINUM`
        and `10` or greater for `DIAMOND`.

    Formatting flags:
    * `''`: (blank) The certification in "mult (if has one) x cert symbol"
        form.
    * `'s'`: (symbol) The same as the blank call, with normal symbols.
        Will not split 11x Diamond into 1x Diamond and 1x Platinum
    * `'S'`: (expanded symbol) Returns the certification as symbols, with
        diamond certification expanded into diamond and platinum.
    * `'f'`: (full) The certification with the full words instead of
        symbols.
    * `'F'`: (expanded full) The certification with the full words and
        diamond expanded.

    Additionally supports sorting, formatting and equality comparison.
    """

    __slots__ = ()

    @classmethod
    def from_units(cls, units: NonNegativeInt) -> 'AlbumCert':
        """
        Returns a new AlbumCert object from the units specified.
        """

        mult = 0
        if units < 500:
            cert = CertType.NONE
        elif units < 1000:
            cert = CertType.GOLD
        elif units < 10_000:
            if units >= 2000:
                mult = units // 1000
            cert = CertType.PLATINUM
        else:
            mult = units // 1000
            cert = CertType.DIAMOND

        return cls(mult, cert)

    def to_units(self) -> int:
        """Returns the certification as the units it represents."""

        if self.cert in (CertType.PLATINUM, CertType.DIAMOND):
            return self._mult * 1000

        if self.cert is CertType.GOLD:
            return 500

        return 0
