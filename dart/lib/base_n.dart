library base_N.base_n;

import "dart:convert";
import "dart:typed_data";
import 'dart:math';
import "package:crypto/crypto.dart" show sha256;

int _logint(int v) => (log(v) * 10000).truncate();

final int ln_256 = _logint(256);

final alphabets = Map.unmodifiable({
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
});

var _cached_alphabets = {};

class Alphabet {
  final String key;
  final List<int> _forward;
  final Map<int, int> _inverse;
  final int ln_base;

  factory Alphabet(String text) {
    return _cached_alphabets.putIfAbsent(text, () => Alphabet._internal(text));
  }

  Alphabet._internal(text)
      : key = text,
        _forward = List.unmodifiable(text.runes),
        _inverse = Map.unmodifiable(Map.fromIterables(
            text.runes, List.generate(text.length, (i) => i))),
        ln_base = _logint(text.length);

  factory Alphabet.predefined(int id) {
    return Alphabet(alphabets[id]);
  }

  int get length => key.length;

  List<int> to_digits(String chars) => [for (var c in chars.runes) _inverse[c]];

  String to_chars(List<int> digits) =>
      String.fromCharCodes([for (var d in digits) _forward[d]]);

  int divmod256(List<int> digits, int startAt) {
    int remaining = 0;
    for (int i = startAt; i < digits.length; i++) {
      int num = this.length * remaining + (digits[i] & 0xFF);
      digits[i] = num ~/ 256;
      remaining = num % 256;
    }
    return remaining;
  }

  int divmodBase(List<int> number, int startAt) {
    int remaining = 0;
    for (int i = startAt; i < number.length; i++) {
      int num = (0xFF & remaining) * 256 + number[i];
      number[i] = num ~/ this.length;
      remaining = num % this.length;
    }
    return remaining;
  }

  int encodeSize(int bytesSize) => 1 + (bytesSize * ln_256) ~/ ln_base;

  int decodeSize(int digitsSize) => 1 + (digitsSize * ln_base) ~/ ln_256;
}

List<int> _sha256x2(List<int> b) =>
    sha256.convert(sha256.convert(b).bytes).bytes;

bool _list_equals(
    List<int> list1, int offset1, List<int> list2, int offset2, int count) {
  for (int i = 0; i < count; i++) {
    if (list1[offset1 + i] != list2[offset2 + i]) {
      return false;
    }
  }
  return true;
}

abstract class BaseN extends Codec<List<int>, String> {
  final Alphabet alphabet;
  DigitsEncoder _encoder;
  DigitsDecoder _decoder;

  List<int> encodeDigits(List<int> bytes);
  List<int> decodeDigits(List<int> digits);

  String encodeCheck(List<int> bytes) {
    Uint8List buffer = Uint8List(bytes.length + 4);
    buffer.setRange(0, bytes.length, bytes);
    List<int> checksum = _sha256x2(bytes.sublist(0, bytes.length));
    buffer.setRange(bytes.length, buffer.length, checksum);
    return encode(buffer);
  }

  List<int> decodeCheck(String code) {
    List<int> bytes = decode(code);
    int payloadEnd = bytes.length - 4;
    Uint8List buffer = Uint8List.fromList(bytes.sublist(0, payloadEnd));
    List<int> checksum = _sha256x2(buffer);
    if (!_list_equals(checksum, 0, bytes, payloadEnd, 4)) {
      throw FormatException('Checksum does not match');
    }
    return buffer;
  }

  BaseN(Alphabet _alphabet) : alphabet = _alphabet {
    _encoder = DigitsEncoder(this);
    _decoder = DigitsDecoder(this);
  }

  @override
  Converter<List<int>, String> get encoder => _encoder;

  @override
  Converter<String, List<int>> get decoder => _decoder;
}

int countleadingZeros(List<int> digits) {
  int z = 0;
  while (z < digits.length && digits[z] == 0) z++;
  return z;
}

class DigitsEncoder extends Converter<List<int>, String> {
  final BaseN logic;
  DigitsEncoder(BaseN this.logic);

  @override
  String convert(List<int> bytes) =>
      logic.alphabet.to_chars(logic.encodeDigits(List.from(bytes)));
}

class DigitsDecoder extends Converter<String, List<int>> {
  final BaseN logic;
  DigitsDecoder(BaseN this.logic);

  @override
  List<int> convert(String text) =>
      this.logic.decodeDigits(this.logic.alphabet.to_digits(text));
}

class LoopBaseN extends BaseN {
  LoopBaseN(Alphabet alphabet) : super(alphabet);

  @override
  List<int> encodeDigits(List<int> bytes) {
    if (bytes.length == 0) return [];
    int leadingZeroes = countleadingZeros(bytes);
    int startAt = leadingZeroes;
    int encodeSize = alphabet.encodeSize(bytes.length - leadingZeroes);
    Uint8List out = Uint8List(leadingZeroes + encodeSize);
    int j = out.length;
    int lastNonZero = j;
    while (startAt < bytes.length && leadingZeroes < j) {
      int mod = alphabet.divmodBase(bytes, startAt);
      if (bytes[startAt] == 0) startAt++;
      out[--j] = mod;
      if (mod != 0) lastNonZero = j;
    }
    return lastNonZero == leadingZeroes
        ? out
        : out.sublist(lastNonZero - leadingZeroes);
  }

  @override
  List<int> decodeDigits(List<int> digits) {
    if (digits.length == 0) return [];
    int leadingZeroes = countleadingZeros(digits);
    int startAt = leadingZeroes;
    int decodeSize = alphabet.decodeSize(digits.length - leadingZeroes);
    Uint8List out = new Uint8List(leadingZeroes + decodeSize);
    int j = out.length;
    int lastNonZero = j;
    while (startAt < digits.length && leadingZeroes < j) {
      int mod = alphabet.divmod256(digits, startAt);
      if (digits[startAt] == 0) startAt++;
      out[--j] = mod;
      if (mod != 0) lastNonZero = j;
    }
    return lastNonZero == leadingZeroes
        ? out
        : out.sublist(lastNonZero - leadingZeroes);
  }
}

//TODO: class BigIntBaseN extends BaseN {}
