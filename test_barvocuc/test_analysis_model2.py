import os
import math

import pytest

from barvocuc import ImageAnalyzer
from barvocuc.settings import Settings


basedir = os.path.dirname(__file__)


TEST_IMG_W = 416
TEST_IMG_H = 200


def open_analyzer(test_file_name):
    settings = Settings()
    settings.model_version = 2
    with open(os.path.join(basedir, test_file_name), 'rb') as f:
        analyzer = ImageAnalyzer(f, settings=settings)
    return analyzer


@pytest.fixture
def analysis():
    return open_analyzer('palette_test.png')


@pytest.fixture
def analysis_gray():
    return open_analyzer('palette_test_gray.png')

def test_matrix_shape_rgba(analysis):
    assert analysis.arrays['rgba'].shape == (TEST_IMG_H, TEST_IMG_W, 4)


@pytest.mark.parametrize('channel', ['r', 'g', 'b', 'a', 'h', 's', 'l',
                                     'sobel_x', 'sobel_y', 'sobel',
                                     'white', 'gray', 'black', 'colorful',
                                     'red', 'orange', 'yellow', 'green',
                                     'blue', 'purple', 'pink',
                                     ])
def test_matrix_shapes_channel(analysis, channel):
    assert analysis.arrays[channel].shape == (TEST_IMG_H, TEST_IMG_W)


@pytest.mark.parametrize('name', ['rgba', 'img_source', 'img_sobel',
                                  'img_colors', 'img_opacity',
                                  ])
def test_matrix_shapes_img(analysis, name):
    assert analysis.arrays[name].shape == (TEST_IMG_H, TEST_IMG_W, 4)


@pytest.mark.parametrize(
    ['name', 'result'],
    [
        ('width', 416),
        ('height', 200),

        ('opaque_pixels', 82821.552941176473),
        ('opacity', 0.99545135746606339),

        ('white', 0.063811892101970608),
        ('black', 0.30867024478235655),
        ('gray',  0.061138438152122575),

        ('red', 0.17183932798396326),
        ('orange', 0.093478082999707945),
        ('yellow', 0.082780337182288818),
        ('green', 0.12927098260299394),
        ('blue', 0.12255264046073826),
        ('purple', 0.059742902955638715),
        ('pink', 0.027009877508440541),

        ('avg_h', 18.152650576308961),
        ('avg_s', 0.7849664022859939),
        ('avg_l', 0.36097501392765707),

        ('stddev_h', 87.073142794455634),
        ('stddev_s', 0.34326393986482562),
        ('stddev_l', 0.25013347556176846),
    ])
def test_concrete_result(analysis, name, result):
    assert math.isclose(analysis.results[name], result)


def test_csv_results(analysis):
    expected = {
        'width': 416,
        'height': 200,
        'white%': 6.3811892101970606,
        'black%': 30.867024478235656,
        'gray%': 6.1138438152122578,
        'red%': 17.183932798396327,
        'orange%': 9.3478082999707937,
        'yellow%': 8.2780337182288815,
        'green%': 12.927098260299394,
        'blue%': 12.255264046073826,
        'purple%': 5.974290295563871,
        'pink%': 2.7009877508440541,
        'avg_h': 18.152650576308961,
        'avg_s': 0.7849664022859939,
        'avg_l': 0.36097501392765707,
        'stddev_h': 87.073142794455634,
        'stddev_s': 0.34326393986482562,
        'stddev_l': 0.25013347556176846,
        'avg_sobel': 0.29800489869539376,
        'opacity%': 99.545135746606334,
        'opaque_pixels': 82821.552941176473,
    }
    got = analysis.csv_results
    assert sorted(got) == sorted(expected)
    for key, value in sorted(expected.items()):
        print(key)
        assert math.isclose(got[key], value)


@pytest.mark.parametrize(
    ['name', 'result'],
    [
        ('width', 416),
        ('height', 200),

        ('opaque_pixels', 82821.552941176473),
        ('opacity', 0.99545135746606339),

        ('white', 0.098899377144227307),
        ('black', 0.39217086430471632),
        ('gray',  0.50892975855105627),

        ('red', 0),
        ('orange', 0),
        ('yellow', 0),
        ('green', 0),
        ('blue', 0),
        ('purple', 0),
        ('pink', 0),

        ('avg_h', None),
        ('avg_s', 0),
        ('avg_l', 0.35081545023797989),

        ('stddev_h', None),
        ('stddev_s', 0),
        ('stddev_l', 0.28612100382292321,),
    ])
def test_concrete_result_gray(analysis_gray, name, result):
    got = analysis_gray.results[name]
    if result is None:
        assert math.isnan(got)
    else:
        assert math.isclose(got, result)


def test_gray_complete(analysis_gray):
    white = analysis_gray.results['white']
    black = analysis_gray.results['black']
    gray = analysis_gray.results['gray']
    assert math.isclose(white + black + gray, 1)


@pytest.mark.parametrize(
    ['filename', 'hue'],
    [
        ('pure_red.png', 0),
        ('cyan_red.png', 90),
        ('magenta_yellow.png', 0),
    ])
def test_hues(filename, hue):
    assert open_analyzer(filename).results['avg_h'] == hue


def test_orig_img_array(analysis):
    assert (analysis.arrays['img_source'] == analysis.arrays['rgba']).all()


@pytest.mark.parametrize('name', ['source', 'sobel',  'colors', 'opacity'])
def test_img_attrs(analysis, name):
    assert analysis.images[name].width == TEST_IMG_W
    assert analysis.images[name].height == TEST_IMG_H
    assert analysis.images[name].format == 'RGBA'


def test_montage_attrs(analysis):
    assert analysis.images['montage'].width == TEST_IMG_W * 2
    assert analysis.images['montage'].height == TEST_IMG_H * 2
    assert analysis.images['montage'].format == 'RGBA'
