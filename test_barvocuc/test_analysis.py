import os
import math

import pytest

from barvocuc import ImageAnalyzer


basedir = os.path.dirname(__file__)


TEST_IMG_W = 416
TEST_IMG_H = 200


def open_analyzer(test_file_name):
    with open(os.path.join(basedir, test_file_name), 'rb') as f:
        return ImageAnalyzer(f)


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

        ('opaque_pixels', 82498.03125),
        ('opacity', 0.9915628756),

        ('white', 0.0635583349),
        ('black', 0.3140432423),
        ('gray',  0.0608969551),

        ('red', 0.1712959912),
        ('orange', 0.0930192652),
        ('yellow', 0.0820800364),
        ('green', 0.1277013429),
        ('blue', 0.1211278906),
        ('purple', 0.0589822314),
        ('pink', 0.0266355788),

        ('avg_h', 18.0988293378),
        ('avg_s', 0.780140703333),
        ('avg_l', 0.35956495528),

        ('stddev_h', 86.9203611561),
        ('stddev_s', 0.341656456209),
        ('stddev_l', 0.249156391673),
    ])
def test_concrete_result(analysis, name, result):
    assert math.isclose(analysis.results[name], result)


def test_csv_results(analysis):
    assert analysis.csv_results == {
        'width': 416,
        'height': 200,
        'white%': 6.3558334914810475,
        'black%': 31.404324231979778,
        'gray%': 6.0896955116731952,
        'red%': 17.129599115433436,
        'orange%': 9.3019265232465767,
        'yellow%': 8.2080036379656018,
        'green%': 12.770134287295493,
        'blue%': 12.112789055193362,
        'purple%': 5.8982231394158271,
        'pink%': 2.6635578803585083,
        'avg_h': 18.098829337769523,
        'avg_s': 0.78014070333343444,
        'avg_l': 0.35956495527950216,
        'stddev_h': 86.920361156144907,
        'stddev_s': 0.34165645620949558,
        'stddev_l': 0.24915639167285492,
        'avg_sobel': 0.29684081705986493,
    }


@pytest.mark.parametrize(
    ['name', 'result'],
    [
        ('width', 416),
        ('height', 200),

        ('opaque_pixels', 82498.03125),
        ('opacity', 0.9915628756),

        ('white', 0.0988993771),
        ('black', 0.3984128220),
        ('gray',  0.5026878009),

        ('red', 0),
        ('orange', 0),
        ('yellow', 0),
        ('green', 0),
        ('blue', 0),
        ('purple', 0),
        ('pink', 0),

        ('avg_h', None),
        ('avg_s', 0),
        ('avg_l', 0.349445077385),

        ('stddev_h', None),
        ('stddev_s', 0),
        ('stddev_l', 0.2850033437),
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
