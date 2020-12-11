library base_N.test;

import "package:test/test.dart";

import "package:base_N/base_n.dart";

import "test_utils.dart";

List<List<String>> _bitcoinVectors = [
  ["", ""],
  ["61", "2g"],
  ["626262", "a3gV"],
  ["636363", "aPEr"],
  ["73696d706c792061206c6f6e6720737472696e67", "2cFupjhnEsSn59qHXstmK2ffpLv2"],
  [
    "00eb15231dfceb60925886b67d065299925915aeb172c06647",
    "1NS17iag9jJgTHD1VXjvLCEnZuQ3rJDE9L"
  ],
  ["516b6fcd0f", "ABnLTmg"],
  ["bf4f89001e670274dd", "3SEo3LWLoPntC"],
  ["572e4794", "3EFU7m"],
  ["ecac89cad93923c02321", "EJDM8drfXA6uyA"],
  ["10c8511e", "Rt5zm"],
  ["00000000000000000000", "1111111111"]
];

void main() {
  group("base_N.base_n", () {
    test("hexToBytes", () {
      expect([254], hexToBytes("fe"));
    });
    test("Alphabet", () {
      Alphabet abc = Alphabet("abc");
      expect('cba', abc.to_chars([2, 1, 0]));
      expect(3, abc.length);
      expect([0, 0, 2, 1], abc.to_digits('aacb'));
    });
    test("bitcoin_vectors", () {
      BaseN codec = LoopBaseN(Alphabet.predefined(58));
      for (List<String> vector in _bitcoinVectors) {
        List<int> bytes = hexToBytes(vector[0]);
        String encoding = vector[1];
        expect(codec.encode(bytes), equals(encoding),
            reason: "encode " + vector.toString());
        expect(codec.decode(encoding), equals(bytes),
            reason: "decode " + vector.toString());
      }
    });
    test("testSamples", () {
      loadSamples().onDone(() {
        expect(BINS.length, equals(40));
        runThruSamples((id) => BigIntBaseN(Alphabet.predefined(id)) as BaseN);
        runThruSamples((id) => LoopBaseN(Alphabet.predefined(id)) as BaseN);
      });
    });
  });
}

runThruSamples(BaseN value(Alphabet)) {
  var sw = Stopwatch()..start();
  Map<int, BaseN> codecs = Map.fromIterable(alphabets.keys, value: value);
  ENCODES.forEach((ekey, v) {
    List<int> bytes = BINS[ekey.test_name];
    BaseN c = codecs[ekey.base];
    var encode = c.encode(bytes);
    expect(encode, equals(v));
    expect(c.decode(encode), equals(bytes));
  });
  ENCODES_WITH_CHECK.forEach((ekey, v) {
    List<int> bytes = BINS[ekey.test_name];
    BaseN c = codecs[ekey.base];
    var encode = c.encodeCheck(bytes);
    expect(encode, equals(v));
    expect(c.decodeCheck(encode), equals(bytes));
  });
  print('${codecs[58].runtimeType}:${sw.elapsedMicroseconds}');
}
