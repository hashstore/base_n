import "dart:typed_data";
import "dart:io";
import "dart:collection";
import 'package:path/path.dart' as p;

List<int> hexToBytes(String hex) {
  if (hex.length % 2 != 0) hex = "0" + hex;
  Uint8List result = new Uint8List(hex.length ~/ 2);
  for (int i = 0; i < result.length; i++) {
    result[i] = int.parse(hex.substring(i * 2, (i + 1) * 2), radix: 16);
  }
  return result;
}

Map<String, List<int>> BINS = new HashMap();
Map<EncodesKey, String> ENCODES_WITH_CHECK = new HashMap();
Map<EncodesKey, String> ENCODES = new HashMap();

class EncodesKey {
  String test_name;
  int base;

  EncodesKey(this.test_name, this.base);

  bool operator ==(o) =>
      o is EncodesKey && test_name == o.test_name && base == o.base;
  
  int get hashCode =>
      [test_name.hashCode, base.hashCode].fold(17, (p, h) => p * 31 + h);

}

const BENCH_DIR = '../benchmark';

Future<void> loadSamples() async {
  var dir = new Directory(BENCH_DIR + '/samples');
  await for(var e in dir.list()) {
    if ( e is File) {
      File f = e;
      var path = f.path;
      var test_name = p.basenameWithoutExtension(path);
      var ext = p.extension(path);
      if (ext == ".bin") {
        BINS[test_name] = await f.readAsBytes();
      } else if (ext.startsWith(".ewc")) {
        ENCODES_WITH_CHECK[EncodesKey(test_name, int.parse(ext.substring(4)))] =
            await f.readAsString();
      } else if (ext.startsWith(".e")) {
        ENCODES[EncodesKey(test_name, int.parse(ext.substring(2)))] =
            await f.readAsString();
      }
    }
  }
}
