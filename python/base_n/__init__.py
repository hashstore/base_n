"""
base_n encoding is just like base58, but allow to use flexible alphabet.

https://en.wikipedia.org/wiki/Base58

Original algorithm is taken from python base58 project
https://github.com/keis/base58 (MIT license)
and generalized for any alphabet

and list of alphabets is taken from
https://github.com/cryptocoinjs/base-x (MIT license)

I believe MIT license is compatible with Apache (if I am wrong,
file bug, don't sue me), so consider this file dual licensed
under Apache and MIT.
"""

from hashlib import sha256
from typing import Dict, List, Tuple, Union, NamedTuple
from math import log, ceil

alphabets = {
    2: "01",
    8: "01234567",
    11: "0123456789a",
    16: "0123456789abcdef",
    32: "0123456789ABCDEFGHJKMNPQRSTVWXYZ",
    36: "0123456789abcdefghijklmnopqrstuvwxyz",
    58: "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz",
    62: "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    64: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    67: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~",
}

def _logint(n)->int:
    return int(log(n) * 10000)

LN_256 = _logint(256)

class CodecDirection(NamedTuple):
    bases: Tuple[int,int]
    logs: Tuple[int,int]

    def aproximate_size(self, size: int) -> int:
        return ceil(size * self.logs[0]/self.logs[1])


class Alphabet:
    def __init__(self, alphabet: str) -> None:
        self.key = alphabet
        self.zero = self.key[0]
        self.base = len(alphabet)
        self.index = {alphabet[i]: i for i in range(self.base)}
        ln_base = _logint(self.base)
        self.encode_direction = CodecDirection((256, self.base),(LN_256, ln_base))
        self.decode_direction = CodecDirection((self.base, 256),(ln_base, LN_256))
        
    def __str__(self):
        return self.key

    def to_digits(self, encoded:str)->List[int]:
        return [ self.index[ch] for ch in encoded]

    def to_chars(self, digits:List[int]) -> str:
        return ''.join( self.key[d] for d in digits)


_cached_alphabets = {}

def ensure_alphabet(abc:Union[Alphabet,str,int]) -> Alphabet:
    if isinstance(abc, Alphabet):
        return abc
    if isinstance(abc, int):
        abc = alphabets[abc]
    if isinstance(abc, str):
        if abc not in _cached_alphabets:
            _cached_alphabets[abc] = Alphabet(abc)
        return _cached_alphabets[abc]
    raise AssertionError("incompatible args: %r" % abc)
    
class BaseN:
    def __init__(self, alphabet: Union[Alphabet,str,int]) -> None:
        self.alphabet = ensure_alphabet(alphabet)

    
    def _code(self, v: List[int], direction: CodecDirection) -> List[int]:
        """ placeholder, need to be overridden"""
        return []

    def encode(self, v: bytes) -> str:
        """Encode a string"""
        if not isinstance(v, bytes):
            raise TypeError(
                "a bytes-like object is required, not '%s'" % type(v).__name__
            )

        origlen = len(v)
        v = v.lstrip(b"\0")
        count_of_nulls = origlen - len(v)
        digits = self._code(list(v), self.alphabet.encode_direction)
        return self.alphabet.zero * count_of_nulls + self.alphabet.to_chars(digits)

    def decode(self, v: str) -> bytes:
        """Decode string"""

        if not isinstance(v, str):
            v = v.decode("ascii")

        origlen = len(v)
        v = v.lstrip(self.alphabet.zero)
        count_of_nulls = origlen - len(v)

        digits = self._code(self.alphabet.to_digits(v), self.alphabet.decode_direction)

        return b"\0" * count_of_nulls + bytes(digits)

    def encode_check(self, v: bytes) -> str:
        """Encode a string with a 4 character checksum"""

        digest = sha256(sha256(v).digest()).digest()
        return self.encode(v + digest[:4])

    def decode_check(self, v: str) -> bytes:
        """Decode and verify the checksum """

        result = self.decode(v)
        result, check = result[:-4], result[-4:]
        digest = sha256(sha256(result).digest()).digest()

        if check != digest[:4]:
            raise ValueError("Invalid checksum")
        return result


def _split_int(i: int, base: int) -> List[int]:
    """split int to digits"""
    result = []
    while i:
        i, digit = divmod(i, base)
        result.insert(0, digit)
    return result

def _combine_int(digits: List[int], base:int) -> int:
    """Combine digits into big integer"""
    acc = 0
    for d in digits:
        acc = acc * base + d
    return acc

def _divmod_buff(buff: List[int], startAt: int, base: int, divisor:int) -> int:
    remaining = 0
    for i in range(startAt, len(buff)):
        num = base * remaining + buff[i]
        buff[i], remaining = divmod(num, divisor)
    return remaining

class BigIntBaseN(BaseN):

    def _code(self, v: List[int], direction: CodecDirection) -> List[int]:
        acc = _combine_int(v, direction.bases[0])
        return _split_int(acc, direction.bases[1])


class LoopBaseN(BaseN):

    def _code(self, v: List[int], direction: CodecDirection) -> List[int]:
        i = 0
        output = []
        last_non_zero = 0
        stop = direction.aproximate_size(len(v))
        while i < len(v) and len(output) < stop:
            mod = _divmod_buff(v, i, *direction.bases)
            if v[i] == 0:
                i += 1
            output.append(mod)
            if mod:
                last_non_zero = len(output)
        return reversed(output[:last_non_zero])


cached_instances: Dict[Tuple[str, str], BaseN] = {}


def base_n(alphabet: Union[Alphabet, int, str], constructor=BigIntBaseN) -> BaseN:
    """
    lazy initialization for BaseN instance

    >>> base_n(58).encode(b'the quick brown fox jumps over the lazy dog')
    '9aMVMYHHtr2a2wF61xEqKskeCwxniaf4m7FeCivEGBzLhSEwB6NEdfeySxW'
    >>> base_n(58).decode('9aMVMYHHtr2a2wF61xEqKskeCwxniaf4m7FeCivEGBzLhSEwB6NEdfeySxW')
    b'the quick brown fox jumps over the lazy dog'

    >>> base_n(58).encode_check(b'the quick brown fox jumps over the lazy dog')
    'y7WFhoXCMz3M46XhLVWLAfYXde92zQ8FTnKRxzWNmBYTDa67791CqkFDJgmtRff3'
    >>> base_n(58).decode_check('y7WFhoXCMz3M46XhLVWLAfYXde92zQ8FTnKRxzWNmBYTDa67791CqkFDJgmtRff3')
    b'the quick brown fox jumps over the lazy dog'
    >>> base_n(58).decode_check('9aMVMYHHtr2a2wF61xEqKskeCwxniaf4m7FeCivEGBzLhSEwB6NEdfeySxW')
    Traceback (most recent call last):
    ...
    ValueError: Invalid checksum


    :param alphabet: alphabet defined by id, alphabet string, or `Alphabet` instance
                        `alphabets` dictionary
    :return: BaseN
    """
    alphabet = ensure_alphabet(alphabet)
    k = (constructor.__name__, alphabet.key)
    if k not in cached_instances:
        cached_instances[k] = constructor(alphabet)
    return cached_instances[k]
