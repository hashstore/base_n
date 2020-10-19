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
from typing import Dict, List, Tuple, Union

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
    66: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~",
}


class BaseN:
    def __init__(self, alphabet: str) -> None:
        self.alphabet = alphabet
        self.size = len(alphabet)
        self.index = {alphabet[i]: i for i in range(self.size)}

    def encode(self, v: bytes) -> str:
        """Encode a string"""
        if not isinstance(v, bytes):
            raise TypeError(
                "a bytes-like object is required, not '%s'" % type(v).__name__
            )

        origlen = len(v)
        v = v.lstrip(b"\0")
        count_of_nulls = origlen - len(v)

        return self.alphabet[0] * count_of_nulls + self._encode_non_nulls(v)

    def _encode_non_nulls(self, v: bytes) -> str:
        pass

    def decode(self, v: str) -> bytes:
        """Decode string"""

        if not isinstance(v, str):
            v = v.decode("ascii")

        # strip null bytes
        origlen = len(v)
        v = v.lstrip(self.alphabet[0])
        count_of_nulls = origlen - len(v)

        return b"\0" * count_of_nulls + self._decode_non_nulls(v)

    def _decode_non_nulls(self, v: str) -> bytes:
        pass

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


class BigIntBaseN(BaseN):
    # def encode_int(self, i: int) -> str:
    #     """Encode an integer"""
    #     if i < 0:
    #         raise AssertionError("uint expected: %r" % i)
    #     return self.alphabet[0] if i == 0 else self._encode_int(i)

    def _encode_int(self, i: int) -> str:
        """unsafe encode_int"""
        string = ""
        while i:
            i, idx = divmod(i, self.size)
            string = self.alphabet[idx] + string
        return string

    def _decode_int(self, v: str) -> int:
        """Decode a string into integer"""

        decimal = 0
        for char in v:
            decimal = decimal * self.size + self.index[char]
        return decimal

    def _decode_non_nulls(self, v: str) -> bytes:
        acc = self._decode_int(v)

        result = []
        while acc > 0:
            acc, mod = divmod(acc, 256)
            result.append(mod)

        return bytes(reversed(result))

    def _encode_non_nulls(self, v: bytes) -> str:
        p, acc = 1, 0
        for c in reversed(v):
            acc += p * c
            p <<= 8

        return self._encode_int(acc)


class LoopBaseN(BaseN):
    def _divmod_base(self, buff: List[int], startAt: int) -> int:
        remaining = 0
        for i in range(startAt, len(buff)):
            num = remaining * 256 + buff[i]
            buff[i], remaining = divmod(num, self.size)
        return remaining

    def _divmod_256(self, buff: List[int], startAt: int) -> int:
        remaining = 0
        for i in range(startAt, len(buff)):
            num = self.size * remaining + buff[i]
            buff[i], remaining = divmod(num, 256)
        return remaining

    def _decode_non_nulls(self, v: str) -> bytes:
        v = [self.index[ch] for ch in v]
        i = 0
        output = []
        while i < len(v):
            mod = self._divmod_256(v, i)
            if v[i] == 0:
                i += 1
            output.append(mod)
        return bytes(reversed(output)).lstrip(b"\0")

    def _encode_non_nulls(self, v: bytes) -> str:
        v = [n for n in v]
        output = []
        i = 0
        while i < len(v):
            mod = self._divmod_base(v, i)
            if v[i] == 0:
                i += 1
            output.append(self.alphabet[mod])

        return "".join(reversed(output))


cached_instances: Dict[Tuple[str, str], BaseN] = {}


def base_n(alphabet: Union[int, str], constructor=BigIntBaseN) -> BaseN:
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


    :param alphabet_id: reference to predefined alphabet from
                        `alphabets` dictionary
    :return: BaseN
    """
    alphabet_id = None
    if isinstance(alphabet, int):
        alphabet_id = alphabet
        alphabet = alphabets[alphabet_id]
    k = (constructor.__name__, alphabet)
    if alphabet not in cached_instances:
        cached_instances[k] = constructor(alphabet)
    return cached_instances[k]
