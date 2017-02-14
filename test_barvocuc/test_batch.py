import os
import io
import sys
import csv
import math
import itertools

import pytest

from barvocuc.batch import generate_csv
from barvocuc.settings import Settings


basedir = os.path.dirname(__file__)

def example_filename(name):
    return os.path.join(basedir, 'examples', name)


def assert_csv_same(a, b):
    reader_a = csv.reader(a)
    reader_b = csv.reader(b)
    zip_longest = itertools.zip_longest
    for i, (line_a, line_b) in enumerate(zip_longest(reader_a, reader_b)):
        print('A line {}: {}'.format(i, line_a))
        print('B line {}: {}'.format(i, line_b))
        if line_a is None or line_b is None:
            raise AssertionError('File lengths differ')
        for j, (val_a, val_b) in enumerate(zip_longest(line_a, line_b)):
            if val_a is None or val_b is None:
                raise AssertionError('Line lengths differ')
            if val_a == val_b:
                continue

            try:
                val_a = float(val_a)
                val_b = float(val_b)
            except ValueError:
                print('string: {} vs {}'.format(val_a, val_b))
                assert val_a == val_b
            else:
                print('float: {} vs {}'.format(val_a, val_b))
                assert math.isclose(val_a, val_b)


@pytest.mark.parametrize('lang', ['cs', 'en'])
def test_gen_csv_cs(lang):
    with open(example_filename('test_settings.dat'), encoding='utf-8') as f:
        settings = Settings.load_from(f)
    settings.lang = lang

    with io.StringIO() as f:
        generate_csv(f, [basedir], settings=settings)
        got = f.getvalue()

    with open(os.path.join(basedir, 'expected_{}.csv'.format(lang)),
            encoding='utf-8') as expected_f:

        with io.StringIO(got) as got_f:
            assert_csv_same(got_f, expected_f)


def assert_dirs_same(adir, bdir):
    al = sorted(os.listdir(adir))
    bl = sorted(os.listdir(bdir))
    assert al == bl
    for a, b in zip(al, bl):
        fulla = os.path.join(adir, a)
        fullb = os.path.join(bdir, b)
        print('a =', fulla)
        print('b =', fullb)
        if os.path.isdir(fulla):
            assert os.path.isdir(fullb)
            assert_dirs_same(fulla, fullb)
        else:
            assert not os.path.isdir(fullb)
            if fulla.endswith('.csv'):
                with open(fulla, 'r') as af, open(fullb, 'r') as bf:
                    assert_csv_same(af, bf)
            else:
                with open(fulla, 'rb') as af, open(fullb, 'rb') as bf:
                    assert af.read() == bf.read()


def test_gen_dir(tmpdir):
    with open(example_filename('test_settings.dat'), encoding='utf-8') as f:
        settings = Settings.load_from(f)

    with io.StringIO() as f:
        generate_csv(f, [basedir], settings=settings, outdir=str(tmpdir))
        got = f.getvalue()
    assert_dirs_same(str(tmpdir), os.path.join(basedir, 'expected_dir'))


def test_single_image(tmpdir):
    with open(example_filename('test_settings.dat'), encoding='utf-8') as f:
        settings = Settings.load_from(f)

    filename = os.path.join(basedir, 'palette_test.png')
    with io.StringIO() as f:
        generate_csv(f, [filename], settings=settings, outdir=str(tmpdir))
        got = f.getvalue()
    assert_dirs_same(str(tmpdir), os.path.join(basedir, 'expected_dir_single'))
