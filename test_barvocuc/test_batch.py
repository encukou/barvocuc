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
