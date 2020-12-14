package base_n

import (
	"bytes"
	"crypto/sha256"
	"fmt"
	"math"
	"math/big"
)

var Alphabets = map[int]string{
	2:  "01",
	8:  "01234567",
	11: "0123456789a",
	16: "0123456789abcdef",
	32: "0123456789ABCDEFGHJKMNPQRSTVWXYZ",
	36: "0123456789abcdefghijklmnopqrstuvwxyz",
	58: "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz",
	62: "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
	64: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
	67: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~",
}

type CodecDirection struct {
	from_base int
	to_base   int
	from_log  int
	to_log    int
}

func logInt(base int) int {
	return int(math.Log(float64(base)) * 10000)
}

func Direction(from_base int, to_base int) CodecDirection {
	return CodecDirection{from_base, to_base, logInt(from_base), logInt(to_base)}
}

func (cd *CodecDirection) approximateSize(size int) int {
	return 1 + size*cd.from_log/cd.to_log
}

func (cd *CodecDirection) divmod(digits []byte, startAt int) int {
	remaining := 0
	for i := startAt; i < len(digits); i++ {
		num := cd.from_base*remaining + int(digits[i])
		digits[i] = byte(num / cd.to_base)
		remaining = num % cd.to_base
	}
	return remaining
}

type Alphabet struct {
	key              []byte
	index            map[byte]byte
	encode_direction CodecDirection
	decode_direction CodecDirection
}

var alphabet_cache = make(map[string]*Alphabet)

func GetAlphabetById(id int) (*Alphabet, error) {
	return GetAlphabet(Alphabets[id])
}

func GetAlphabet(alphabet string) (*Alphabet, error) {
	abc, ok := alphabet_cache[alphabet]
	if !ok {
		base := len(alphabet)
		key := make([]byte, base)
		index := make(map[byte]byte)
		for i := 0; i < base; i++ {
			if alphabet[i] >= 0 && alphabet[i] < 128 {
				ch := alphabet[i]
				key[i] = ch
				index[ch] = byte(i)
			} else {
				return nil, fmt.Errorf("Non ASCII character %#x in alphabet at:%d", alphabet[i], i)
			}
		}
		abc = &Alphabet{key, index, Direction(256, base), Direction(base, 256)}
	}
	return abc, nil
}

func (abc *Alphabet) toDigits(encoded string) []byte {
	var count = len(encoded)
	var digits = make([]byte, count)
	for i := 0; i < count; i++ {
		digits[i] = abc.index[byte(encoded[i])]
	}
	return digits
}

func (abc *Alphabet) toChars(digits []byte) string {
	var count = len(digits)
	var chars = make([]rune, count)
	for i := 0; i < count; i++ {
		chars[i] = rune(abc.key[digits[i]])
	}
	return string(chars)
}

func sha256x2(data []byte) []byte {
	step1 := sha256.Sum256(data)
	step2 := sha256.Sum256(step1[:])
	return step2[:]
}

func countLeadingZeros(digits []byte) int {
	z := 0
	for z < len(digits) && digits[z] == 0 {
		z++
	}
	return z
}

type Codec struct {
	abc          *Alphabet
	cloneBuffer  bool
	repackDigits func(CodecDirection, []byte, []byte, int) int
}
type CodecId int

var CodecSettings = []struct {
	name         string
	cloneBuffer  bool
	repackDigits func(CodecDirection, []byte, []byte, int) int
}{
	{"Loop", true, repackWithLoop},
	{"BigInt", false, repackWithBigInt},
}

const (
	Loop CodecId = iota
	BigInt
)

func (cid CodecId) String() string {
	return CodecSettings[cid].name
}

func (cid CodecId) NewCodec(abc *Alphabet) *Codec {
	settings := CodecSettings[cid]
	return &Codec{abc, settings.cloneBuffer, settings.repackDigits}
}

func (cc *Codec) codeDigits(digits []byte, direction CodecDirection) []byte {
	if len(digits) == 0 {
		return digits
	}
	leadingZeros := countLeadingZeros(digits)
	codeSize := direction.approximateSize(len(digits) - leadingZeros)
	out := make([]byte, leadingZeros+codeSize)
	firstNonZero := cc.repackDigits(direction, digits, out, leadingZeros)
	if firstNonZero == leadingZeros {
		return out
	}
	return out[firstNonZero-leadingZeros:]
}

func repackWithLoop(direction CodecDirection, from []byte, to []byte, leadingZeros int) int {
	startAt := leadingZeros
	j := len(to)
	firstNonZero := j
	for startAt < len(from) && leadingZeros < j {
		mod := direction.divmod(from, startAt)
		if from[startAt] == 0 {
			startAt++
		}
		j--
		to[j] = byte(mod)
		if mod != 0 {
			firstNonZero = j
		}
	}
	return firstNonZero
}

var bigZero = big.NewInt(0)

func repackWithBigInt(direction CodecDirection, from []byte, to []byte, leadingZeros int) int {
	var base1 = big.NewInt(int64(direction.from_base))
	var base2 = big.NewInt(int64(direction.to_base))
	var acc = big.NewInt(0)
	for i := leadingZeros; i < len(from); i++ {
		acc.Mul(acc, base1)
		acc.Add(acc, big.NewInt(int64(from[i])))
	}
	j := len(to)
	firstNonZero := j
	bigMod := big.NewInt(0)
	for acc.Cmp(bigZero) > 0 {
		acc.DivMod(acc, base2, bigMod)
		mod := byte(bigMod.Int64())
		j--
		to[j] = mod
		if mod != 0 {
			firstNonZero = j
		}
	}
	return firstNonZero
}

func (cc *Codec) encodeDigits(digits []byte) string {
	return cc.abc.toChars(cc.codeDigits(digits, cc.abc.encode_direction))
}

func CopyBytes(src []byte, dest []byte, offset int) []byte {
	srcLen := len(src)
	destLen := len(dest)
	for i := 0; i < srcLen; i++ {
		j := offset + i
		if j < destLen {
			dest[j] = src[i]
		} else {
			break
		}
	}
	return dest
}

func (cc *Codec) Encode(buffer []byte) string {
	if !cc.cloneBuffer {
		return cc.encodeDigits(buffer) // cloning not necessary for BigInt implementation
	}
	return cc.encodeDigits(CopyBytes(buffer, make([]byte, len(buffer)), 0))
}

func (cc *Codec) Decode(text string) []byte {
	return cc.codeDigits(cc.abc.toDigits(text), cc.abc.decode_direction)
}

func (cc *Codec) EncodeCheck(buffer []byte) string {
	rawLen := len(buffer)
	bufWithCheck := CopyBytes(buffer, make([]byte, rawLen+4), 0)
	CopyBytes(sha256x2(buffer), bufWithCheck, rawLen)
	return cc.encodeDigits(bufWithCheck)
}

func (cc *Codec) DecodeCheck(text string) ([]byte, error) {
	buffer := cc.Decode(text)
	payloadLen := len(buffer) - 4
	out := buffer[:payloadLen]
	sha := sha256x2(out)
	if !bytes.Equal(sha[:4], buffer[payloadLen:]) {
		return nil, fmt.Errorf("Checksum does not match")
	}
	return out, nil
}
