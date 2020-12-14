library base_N.base_n;

import "dart:convert";
import "dart:typed_data";
import 'dart:math';
import "package:crypto/crypto.dart" show sha256;

int _logint(int v) => (log(v) * 10000).truncate();

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


class CodecDirection {
  final int base1, base2;
  final int log1, log2;

  CodecDirection(this.base1, this.base2)
      : log1 = _logint(base1),
        log2 = _logint(base2);

  int aproximateSize(int size) {
    return 1 + size * log1 ~/ log2;
  }

  int divmod(List<int> digits, int startAt) {
    int remaining = 0;
    for (int i = startAt; i < digits.length; i++) {
      int num = base1 * remaining + digits[i];
      digits[i] = num ~/ base2;
      remaining = num % base2;
    }
    return remaining;
  }
}

var _cached_alphabets = {};

class Alphabet {
  final String key;
  final List<int> _forward;
  final Map<int, int> _inverse;
  final CodecDirection encode_direction;
  final CodecDirection decode_direction;

  Alphabet._internal(text)
      : key = text,
        _forward = List.unmodifiable(text.runes),
        _inverse = Map.unmodifiable(Map.fromIterables(
            text.runes, List.generate(text.length, (i) => i))),
        decode_direction = CodecDirection(text.length, 256),
        encode_direction = CodecDirection(256, text.length);

  factory Alphabet(String text) {
    return _cached_alphabets.putIfAbsent(text, () => Alphabet._internal(text));
  }

  factory Alphabet.predefined(int id) {
    return Alphabet(alphabets[id]);
  }

  List<int> to_digits(String chars) => [for (var c in chars.runes) _inverse[c]];

  String to_chars(List<int> digits) =>
      String.fromCharCodes([for (var d in digits) _forward[d]]);
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

  List<int> codeDigits(List<int> digits, CodecDirection direction) {
    if (digits.length == 0) return [];
    int leadingZeros = countLeadingZeros(digits);
    int codeSize = direction.aproximateSize(digits.length - leadingZeros);
    Uint8List out = Uint8List(leadingZeros + codeSize);
    int firstNonZero = repackDigits(digits, direction, leadingZeros, out);
    return firstNonZero == leadingZeros
        ? out
        : out.sublist(firstNonZero - leadingZeros);
  }

  int repackDigits(List<int> digits, CodecDirection direction, int leadingZeros,
      Uint8List out);

  String encodeCheck(List<int> bytes) {
    Uint8List buffer = Uint8List(bytes.length + 4);
    buffer.setRange(0, bytes.length, bytes);
    List<int> checksum = _sha256x2(bytes);
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

int countLeadingZeros(List<int> digits) {
  int z = 0;
  while (z < digits.length && digits[z] == 0) z++;
  return z;
}

class DigitsEncoder extends Converter<List<int>, String> {
  final BaseN logic;
  DigitsEncoder(BaseN this.logic);

  @override
  String convert(List<int> bytes) => logic.alphabet.to_chars(
      logic.codeDigits(List.from(bytes), logic.alphabet.encode_direction));
}

class DigitsDecoder extends Converter<String, List<int>> {
  final BaseN logic;
  DigitsDecoder(BaseN this.logic);

  @override
  List<int> convert(String text) => this.logic.codeDigits(
      this.logic.alphabet.to_digits(text), logic.alphabet.decode_direction);
}

class LoopBaseN extends BaseN {
  LoopBaseN(Alphabet alphabet) : super(alphabet);

  @override
  int repackDigits(List<int> digits, CodecDirection direction, int leadingZeros,
      Uint8List out) {
    int startAt = leadingZeros;
    int j = out.length;
    int firstNonZero = j;
    while (startAt < digits.length && leadingZeros < j) {
      int mod = direction.divmod(digits, startAt);
      if (digits[startAt] == 0) startAt++;
      out[--j] = mod;
      if (mod != 0) firstNonZero = j;
    }
    return firstNonZero;
  }
}

class BigIntBaseN extends BaseN {
  BigIntBaseN(Alphabet alphabet) : super(alphabet);

  @override
  int repackDigits(List<int> digits, CodecDirection direction, int leadingZeros,
      Uint8List out) {
    var base1 = BigInt.from(direction.base1);
    var base2 = BigInt.from(direction.base2);
    BigInt acc = digits
        .sublist(leadingZeros)
        .fold(BigInt.zero, (p, n) => p * base1 + BigInt.from(n));
    int j = out.length;
    int firstNonZero = j;
    while (acc > BigInt.zero) {
      int mod = (acc % base2).toInt();
      acc = acc ~/ base2;
      out[--j] = mod;
      if (mod != 0) firstNonZero = j;
    }
    return firstNonZero;
  }
}
