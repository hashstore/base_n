import datetime
import sys
from itertools import chain
from pathlib import Path
from random import randint, seed
from typing import Type

import base_n


def random_bytes(sz):
    return bytes(randint(0, 255) for _ in range(sz))


b58 = base_n.base_n(58)


def test_nulls():
    assert b58.decode("12") == b"\x00\x01"
    assert b58.decode(b"12") == b"\x00\x01"
    assert b58.encode(b"\0\1") == "12"
    assert b58.decode("1") == b"\x00"
    assert b58.encode(b"\0") == "1"
    assert b58.decode("") == b""
    assert b58.encode(b"") == ""
    try:
        b58.encode("")
        assert False
    except TypeError:
        pass


def measure(logic, at_least_mills=10):
    delta = datetime.timedelta(microseconds=at_least_mills * 1000)
    number_of_invocations = 0
    start = datetime.datetime.now()
    while True:
        result = logic()
        number_of_invocations += 1
        elapsed = datetime.datetime.now() - start
        if elapsed > delta:
            break
    return result, elapsed.total_seconds() / number_of_invocations


def produce_random_samples():
    seed(0)
    zeropad = [0, 1, *(randint(2, 255) for _ in range(3))]
    for sz in [1, 2, 0, 3, 16, 77, 513, 732]:
        for z in zeropad:
            b = b"\x00" * z + random_bytes(sz)
            test_name = f"z{z}_b{sz}"
            yield test_name, b


def all_codecs(constructor: Type[base_n.BaseN]):
    return (base_n.base_n(k, constructor=constructor) for k in base_n.alphabets)


BENCH_DIR = "../benchmark"


def write_measurements(bench_dir=BENCH_DIR):
    dir = f"{bench_dir}/measurements"
    with open(f"{dir}/{datetime.date.today()}_python_base_n.csv", "wt") as w:
        w.write(
            "algo,sample,alphabet_size,encode_time,decode_time,encoded_with_check_time,decoded_with_check_time\n"
        )
        for t in chain(
            measure_all(10, base_n.BigIntBaseN),
            measure_all(10, base_n.LoopBaseN),
        ):
            w.write(",".join(map(str, t)) + "\n")


def write_samples(bench_dir=BENCH_DIR):
    dir = f"{bench_dir}/samples"
    for test_name, b in produce_random_samples():
        open(f"{dir}/{test_name}.bin", "wb").write(b)
        for codec in all_codecs(base_n.BigIntBaseN):
            open(f"{dir}/{test_name}.e{codec.alphabet.base}", "wt").write(codec.encode(b))
            open(f"{dir}/{test_name}.ewc{codec.alphabet.base}", "wt").write(
                codec.encode_check(b)
            )


BINS = {}
ENCODES_WITH_CHECK = {}
ENCODES = {}


def load_files(bench_dir=BENCH_DIR):
    dir = f"{bench_dir}/samples"
    for f in Path(dir).iterdir():
        test_name = f.stem
        if f.suffix == ".bin":
            BINS[test_name] = f.open("rb").read()
        elif f.suffix.startswith(".ewc"):
            ENCODES_WITH_CHECK[(test_name, int(f.suffix[4:]))] = f.open("rt").read()
        elif f.suffix.startswith(".e"):
            ENCODES[(test_name, int(f.suffix[2:]))] = f.open("rt").read()

def ensure_load_files():
    if len(BINS) == 0 :
        load_files()

def measure_all(mills: int, constructor: Type[base_n.BaseN]):
    for test_name, b in produce_random_samples():
        for codec in all_codecs(constructor):
            encoded, encode_time = measure(lambda: codec.encode(b), mills)
            if len(ENCODES):
                assert ENCODES[(test_name, codec.alphabet.base)] == encoded
            decoded, decode_time = measure(lambda: codec.decode(encoded), mills)
            assert decoded == b
            encoded_with_check, encoded_with_check_time = measure(
                lambda: codec.encode_check(b), mills
            )
            if len(ENCODES_WITH_CHECK):
                assert ENCODES_WITH_CHECK[(test_name, codec.alphabet.base)] == encoded_with_check
            decoded_with_check, decoded_with_check_time = measure(
                lambda: codec.decode_check(encoded_with_check), mills
            )
            assert decoded_with_check == b
            yield constructor.__name__, test_name, codec.alphabet.base, encode_time, decode_time, encoded_with_check_time, decoded_with_check_time

def test_alphabet():
    ensure_load_files()
    for t, alphabet_id in ENCODES :
        if t.startswith('z0_'):
            abc = base_n.ensure_alphabet(alphabet_id)
            binary_l = len(BINS[t])
            encoded_l = len(ENCODES[(t,alphabet_id)])
            assert abc.encode_direction.aproximate_size(binary_l) >= encoded_l
            assert abc.decode_direction.aproximate_size(encoded_l) >= binary_l


def test_all_implementations():
    ensure_load_files()
    for _ in chain(
        measure_all(1, base_n.BigIntBaseN),
        measure_all(1, base_n.LoopBaseN),
    ):
        pass


OPTS = {
    "sample": write_samples,
    "measure": write_measurements,
}
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in OPTS:
        OPTS[sys.argv[1]]()
    else:
        print(f"Pick one: {list(OPTS)}")
