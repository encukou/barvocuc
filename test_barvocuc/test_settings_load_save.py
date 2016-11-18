import os
import io
import json

import pytest

from barvocuc.batch import generate_csv
from barvocuc.settings import Settings, FIELD_NAMES, IMAGE_NAMES


basedir = os.path.dirname(__file__)

def example_filename(name):
    return os.path.join(basedir, 'examples', name)


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def control(settings):
    control = Settings()
    yield control
    assert_settings_equal(settings, control)
    check_roundtrip(settings)


def check_roundtrip(settings):
    first = io.StringIO()
    first_dict = settings.to_dict()
    settings.save_to(first)

    f = io.StringIO(first.getvalue())
    read_settings = Settings.load_from(f)

    second_dict = settings.to_dict()

    assert first_dict == second_dict
    assert json.loads(first.getvalue()) == first_dict


def assert_settings_equal(got, expected):
    for attr_name in dir(expected):
        if not attr_name.startswith('_'):
            expected_attr = getattr(expected, attr_name)
            if not isinstance(expected_attr, type(expected.load_from)):
                got_attr = getattr(got, attr_name)
                print(attr_name)
                assert got_attr == expected_attr


def test_serialization_default(settings):
    result = io.StringIO()
    settings.save_to(result)
    with open(example_filename('default_settings.dat')) as f:
        expected = f.read()
    assert result.getvalue() == expected


def test_deserialization_default():
    with open(example_filename('default_settings.dat')) as f:
        settings = Settings.load_from(f)
    assert_settings_equal(settings, Settings())


def test_from_empty_dict(settings):
    settings.from_dict({})
    assert_settings_equal(settings, Settings())


def test_from_main_thresholds(settings, control):
    new_value = tuple(range(14))
    settings.from_dict({'thresholds': {'color': new_value}})
    control.color_thresholds[:] = new_value

@pytest.mark.parametrize('n', (1, 20))
def test_from_bad_main_thresholds(settings, control, n):
    with pytest.raises(ValueError):
        settings.from_dict({'thresholds': {'color': tuple(range(n))}})

def test_from_special_thresholds(settings, control):
    new_value = {'white': 0.2, 'black': 1, 'gray': 3, 'foo': 5}
    settings.from_dict({'thresholds': {'special': new_value}})
    new_value = dict(new_value)
    del new_value['foo']
    new_value['gray'] = 1
    control.special_thresholds.update(new_value)

def test_from_display_color(settings, control):
    val1 = '#ff8800'
    val2 = '#facade'
    settings.from_dict({'display_colors': {'main': [val1, val2]}})
    control.main_display_colors[0] = 1, 0x88/255, 0
    control.main_display_colors[1] = 0xfa/255, 0xca/255, 0xde/255

def test_from_display_color_all(settings, control):
    val = '#ff8800'
    N = 7
    settings.from_dict({'display_colors': {'main': [val] * N}})
    for i in range(N):
        control.main_display_colors[i] = 1, 0x88/255, 0

def test_from_display_color_too_long(settings, control):
    val = '#ff8800'
    with pytest.raises(ValueError):
        settings.from_dict({'display_colors': {'main': [val] * 100}})

@pytest.mark.parametrize('value', ('bad', '#q31234', '#12121212', 'facade'))
def test_from_bad_display_colors(settings, control, value):
    with pytest.raises(ValueError):
        settings.from_dict({'display_colors': {'main': [value]}})

def test_from_special_color(settings, control):
    val1 = '#ff8800'
    val2 = '#facade'
    settings.from_dict({'display_colors': {'special': [val1, val2]}})
    control.special_display_colors[0] = 1, 0x88/255, 0
    control.special_display_colors[1] = 0xfa/255, 0xca/255, 0xde/255

def test_from_transition_color(settings, control):
    val1 = '#ff8800'
    val2 = '#facade'
    settings.from_dict({'display_colors': {'transition': [val1, val2]}})
    control.transition_display_colors[0] = 1, 0x88/255, 0
    control.transition_display_colors[1] = 0xfa/255, 0xca/255, 0xde/255

def test_from_all_output_fields(settings, control):
    fields = list(FIELD_NAMES['en'])
    fields.insert(0, 'bogus')
    fields.insert(5, 'bogus2')
    fields.append('bogus3')
    settings.from_dict({'output': {'csv_fields': fields}})
    control.csv_output_fields = list(FIELD_NAMES['en'])

def test_from_no_output_fields(settings, control):
    fields = ['bogus', 'bogus2', 'bogus3']
    settings.from_dict({'output': {'csv_fields': fields}})

def test_from_all_output_images(settings, control):
    fields = list(IMAGE_NAMES)
    fields.insert(0, 'bogus')
    fields.insert(3, 'bogus2')
    fields.append('bogus3')
    settings.from_dict({'output': {'images': fields}})
    control.output_images = list(IMAGE_NAMES)

def test_from_no_output_images(settings, control):
    fields = ['bogus', 'bogus2', 'bogus3']
    settings.from_dict({'output': {'images': fields}})

def test_from_lang(settings, control):
    settings.from_dict({'lang': 'cs'})
    control.lang = 'cs'

def test_from_bad_lang(settings, control):
    settings.from_dict({'lang': 'xq'})
    control.lang = 'en'

def test_load_old():
    with open(example_filename('old_settings.dat')) as f:
        settings = Settings.load_from(f)
    assert_settings_equal(settings, Settings())

def test_load_messed_up_old():
    with open(example_filename('messed_up_old_settings.dat')) as f:
        settings = Settings.load_from(f)
    with open(example_filename('messed_up_settings.dat')) as f:
        control = Settings.load_from(f)
    assert_settings_equal(settings, control)
