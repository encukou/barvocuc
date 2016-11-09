import os
import io

import pytest

from barvocuc.batch import generate_csv
from barvocuc.settings import Settings


basedir = os.path.dirname(__file__)

@pytest.mark.parametrize('lang', ['cs', 'en'])
def test_gen_csv_cs(lang):
    settings = Settings()
    settings.lang = lang

    with io.StringIO() as f:
        generate_csv(f, [basedir], settings=settings)
        got = f.getvalue()
    with open(os.path.join(basedir, 'expected_{}.csv'.format(lang))) as f:
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
    settings = Settings()

    with io.StringIO() as f:
        generate_csv(f, [basedir], settings=settings, outdir=str(tmpdir))
        got = f.getvalue()
    assert_dirs_same(str(tmpdir), os.path.join(basedir, 'expected_dir'))
