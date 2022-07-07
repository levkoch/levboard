'''
levboard/main/model/cert.py

Where all of the certifications are held.
'''

from enum import Enum
from pydantic import NonNegativeInt


class CertType(Enum):
    """
    The four different certification types.

    Attributes:
    * `NONE`: Music unit is not certified. Maps to "Un-Certified" or "".
    * `GOLD`: Music unit is certified Gold. Maps to "Gold" or "●".
    * `PLATINUM`: Music unit is certified Platinum or higher. Maps to "Platinum" or "▲".
    * `DIAMOND`: Music unit is certified 10x multi-Platinum or higher. Maps to "Diamond" or "⬥".
    """

    NONE = 'Un-Certified'
    GOLD = 'Gold'
    PLATINUM = 'Platinum'
    DIAMOND = 'Diamond'

    def to_symbol(self) -> str:
        convert = {
            CertType.NONE: '-',
            CertType.GOLD: '●',
            CertType.PLATINUM: '▲',
            CertType.DIAMOND: '⬥',
        }
        return convert[self]


class BaseCert:
    """
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

    __slots__ = ('_cert', '_mult')

    _cert: CertType
    _mult: NonNegativeInt

    def __init__(self, units: NonNegativeInt):
        self._units = units
        self._mult = 0
        self._load()

    def _load(self) -> None:
        raise NotImplementedError(
            'Cannot instantiate an instance of `BaseCert`. '
            'Use a subclass instead.'
        )

    def __str__(self) -> str:
        if self._mult == 0:
            return self._cert.to_symbol()
        return f'{self._mult}x{self._cert.to_symbol()}'

    def __repr__(self) -> str:
        return f'{type(self)}({self._units})'

    def __format__(self, fmt: str) -> str:
        # flags are 's', 'S', 'f', and 'F'
        if not fmt or fmt == 's':
            return str(self)

        if fmt == 'S':
            if self._cert != CertType.DIAMOND:
                return str(self)

            info = self.__format__('F')
            for (f, t) in ((i.value, i.to_symbol()) for i in CertType):
                info = info.replace(f, t)
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

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented   # don't know how to compare
        if self._cert == other._cert:
            return self._mult < other._mult
        if self._cert == CertType.DIAMOND and other._cert != CertType.DIAMOND:
            return False
        if self._cert == CertType.PLATINUM and other._cert == CertType.DIAMOND:
            return True
        if self._cert == CertType.GOLD and other._cert != CertType.NONE:
            return True
        return False

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented   # don't know how to compare
        return (self._cert, self._mult) == (other._cert, other._mult)


class SongCert(BaseCert):
    __doc__ = 'Represents an song certification.\n' + super().__doc__
    __slots__ = ()

    def _load(self) -> None:
        """
        Sets the cert and mult fields with the way that they should be for a song.
        Should only be called once, during construction.
        """

        if self._units < 100:
            self._cert = CertType.NONE
        elif self._units < 200:
            self._cert = CertType.GOLD
        elif self._units < 2000:
            if self._units >= 400:
                self._mult = self._units // 200
            self._cert = CertType.PLATINUM
        else:
            self._mult = self._units // 200
            self._cert = CertType.DIAMOND


class AlbumCert(BaseCert):
    __doc__ = 'Represents an album certification.\n' + super().__doc__
    __slots__ = ()

    def _load(self) -> None:
        """
        Sets the cert and mult fields with the way that they should be for an album.
        Should only be called once, during construction.
        """

        if self._units < 500:
            self._cert = CertType.NONE
        elif self._units < 1000:
            self._cert = CertType.GOLD
        elif self._units < 10000:
            if self._units >= 2000:
                self._mult = self._units // 1000
            self._cert = CertType.PLATINUM
        else:
            self._mult = self._units // 1000
            self._cert = CertType.DIAMOND
