import os
import io
import sys

import pytest

from barvocuc.batch import generate_csv
from barvocuc.settings import Settings


pytestmark = pytest.mark.skipif(sys.platform == 'win32',
                                reason="file format different on windows")

basedir = os.path.dirname(__file__)

def example_filename(name):
    return os.path.join(basedir, 'examples', name)

@pytest.mark.parametrize('lang', ['cs', 'en'])
def test_gen_csv_cs(lang):
    with open(example_filename('test_settings.dat'), encoding='utf-8') as f:
        settings = Settings.load_from(f)
    settings.lang = lang

    with io.StringIO() as f:
        generate_csv(f, [basedir], settings=settings)
        got = f.getvalue()
    with open(os.path.join(basedir, 'expected_{}.csv'.format(lang)),
              encoding='utf-8') as f:
        expected = f.read()
    assert got == expected


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
            with open(fulla, 'rb') as af, open(fullb, 'rb') as bf:
                assert af.read() == bf.read()


def test_gen_dir(tmpdir):
    with open(example_filename('test_settings.dat'), encoding='utf-8') as f:
        settings = Settings.load_from(f)

    with io.StringIO() as f:
        generate_csv(f, [basedir], settings=settings, outdir=str(tmpdir))
        got = f.getvalue()
    assert_dirs_same(str(tmpdir), os.path.join(basedir, 'expected_dir'))
