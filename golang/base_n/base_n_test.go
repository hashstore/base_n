package base_n

import (
	"bytes"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func TestAlphabet(t *testing.T) {
	var tests = []struct {
		id       int
		alphabet string
		err      string
		logbase  int
		log256   int
	}{
		{2, "", "", 6931, 55451},
		{0, "a\xFF", "Non ASCII character 0xff in alphabet at:1", 0, 0},
	}
	for _, c := range tests {
		var abc *Alphabet
		var e error
		if c.alphabet == "" {
			abc, e = GetAlphabetById(c.id)
		} else {
			abc, e = GetAlphabet(c.alphabet)
		}
		if c.err == "" {
			if abc.encode_direction.from_log != c.log256 {
				t.Errorf("id:%d abc.encode_direction.from_log(%d) != log256(%d)", c.id, abc.encode_direction.from_log, c.log256)
			}
			if abc.encode_direction.to_log != c.logbase {
				t.Errorf("id:%d abc.encode_direction.to_log(%d) != logbase(%d)", c.id, abc.encode_direction.to_log, c.logbase)
			}
		} else {
			if e.Error() != c.err {
				t.Errorf("id:%d expected:%s got:%s", c.id, c.err, e.Error())
			}

		}
	}
}

type Sample struct {
	testName string
	base     int
	encode   string
}

var Bins = make(map[string][]byte)
var Encodes = make([]Sample, 0)
var EncodesWithCheck = make([]Sample, 0)

func EnsureLoadSamples(t *testing.T) {
	if len(Bins) != 0 {
		return
	}
	dirname := "../../benchmark/samples"
	dir, err := os.Open(dirname)
	if err != nil {
		t.Errorf("failed opening directory: %s", err)
		return
	}
	defer dir.Close()

	list, _ := dir.Readdirnames(0)
	for _, name := range list {
		ext := filepath.Ext(name)
		path := filepath.Join(dirname, name)
		testName := name[:len(name)-len(ext)]
		if strings.HasPrefix(ext, ".bin") {
			buf, err := ioutil.ReadFile(path)
			if err != nil {
				t.Errorf("failed opening to read: %s %s", path, err)
				return
			}
			Bins[testName] = buf
		} else if strings.HasPrefix(ext, ".ewc") {
			buf, err := ioutil.ReadFile(path)
			if err != nil {
				t.Errorf("failed opening to read: %s %s", path, err)
				return
			}
			base, err2 := strconv.Atoi(ext[4:])
			if err2 != nil {
				t.Errorf("failed opening to read: %s %s", path, err2)
				return
			}
			EncodesWithCheck = append(EncodesWithCheck, Sample{testName, base, string(buf)})
		} else if strings.HasPrefix(ext, ".e") {
			buf, err := ioutil.ReadFile(path)
			if err != nil {
				t.Errorf("failed opening to read: %s %s", path, err)
				return
			}
			base, err2 := strconv.Atoi(ext[2:])
			if err2 != nil {
				t.Errorf("failed opening to read: %s %s", path, err2)
				return
			}
			Encodes = append(Encodes, Sample{testName, base, string(buf)})
		} else {
			fmt.Printf("%s %s %s\n", testName, ext, path)
		}
	}
}

func TestEncodeDecode(t *testing.T) {
	EnsureLoadSamples(t)
	runSamples(t, Loop)
	runSamples(t, BigInt)
}
func runSamples(t *testing.T, cid CodecId) {
	for _, sample := range Encodes {
		bin := Bins[sample.testName]
		abc, e := GetAlphabetById(sample.base)
		if e != nil {
			t.Error(e)
		}
		codec := cid.NewCodec(abc)
		encoded := codec.Encode(bin)
		if sample.encode != encoded {
			t.Errorf("%s %d: %v != %v", sample.testName, sample.base, sample.encode, encoded)
		}
		decoded := codec.Decode(encoded)
		if !bytes.Equal(bin, decoded) {
			t.Errorf("%s %d: binary does not match", sample.testName, sample.base)
		}

	}
	for _, sample := range EncodesWithCheck {
		bin := Bins[sample.testName]
		abc, e := GetAlphabetById(sample.base)
		if e != nil {
			t.Error(e)
		}
		codec := cid.NewCodec(abc)
		encoded := codec.EncodeCheck(bin)
		if sample.encode != encoded {
			t.Errorf("%s %d: %v != %v", sample.testName, sample.base, sample.encode, encoded)
		}
		decoded, e2 := codec.DecodeCheck(encoded)
		if e2 != nil {
			t.Error(e2)
		}
		if !bytes.Equal(bin, decoded) {
			t.Errorf("%s %d: binary does not match", sample.testName, sample.base)
		}

	}
}
