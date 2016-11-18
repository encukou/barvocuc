import json
import collections

COLOR_NAMES = 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink'
SPECIAL_NAMES = 'white', 'gray', 'black', 'colorful', 'opacity'

IMAGE_NAMES = 'source', 'colors', 'sobel', 'opacity', 'montage'

FIELD_NAMES = {
    'en': {
        'filename': 'Filename',
        'width': 'Width',
        'height': 'Height',
        'white': 'White',
        'black': 'Black',
        'gray': 'Gray',
        'red': 'Red',
        'orange': 'Orange',
        'yellow': 'Yellow',
        'green': 'Green',
        'blue': 'Blue',
        'purple': 'Purple',
        'pink': 'Pink',
        'avg_h': 'Avg. H',
        'avg_s': 'Avg. S',
        'avg_l': 'Avg. L',
        'stddev_h': 'Stddev. H',
        'stddev_s': 'Stddev. S',
        'stddev_l': 'Stddev. L',
        'avg_sobel': 'Avg. Sobel',
        'opacity': 'Opacity',
        'opaque_pixels': 'Opaque Pixels',
        'error': 'Error',
    },
    'cs': {
        'filename': 'Jméno souboru',
        'width': 'Šířka',
        'height': 'Výška',
        'white': 'Bílá',
        'black': 'Černá',
        'gray': 'Šedá',
        'red': 'Červená',
        'orange': 'Oranžová',
        'yellow': 'Žlutá',
        'green': 'Zelená',
        'blue': 'Modrá',
        'purple': 'Fialová',
        'pink': 'Růžová',
        'avg_h': 'Prům. H',
        'avg_s': 'Prům. S',
        'avg_l': 'Prům. L',
        'stddev_h': 'Směr. odch. H',
        'stddev_s': 'Směr. odch. S',
        'stddev_l': 'Směr. odch. L',
        'avg_sobel': 'Hrany',
        'opacity': 'Neprůhlednost',
        'opaque_pixels': 'Neprůhledných pixelů',
        'error': 'Chyba programu',
    },
}

for table in FIELD_NAMES.values():
    for ident in SPECIAL_NAMES + COLOR_NAMES:
        name = table.get(ident)
        if name:
            table.setdefault(ident + '%', '% ' + name)


def to_hex(rgb):
    return '#{0:02x}{1:02x}{2:02x}'.format(*(int(c*255) for c in rgb))


def from_hex(hexcolor):
    if len(hexcolor) != 7:
        raise ValueError('bad color: {}'.format(hexcolor))
    if hexcolor[0] != '#':
        raise ValueError('bad color: {}'.format(hexcolor))
    return tuple(clamp(int(hexcolor[i:i+2], 16) / 255, float, 0, 1)
                 for i in range(1, 7, 2))


def clamp(n, type, a, b):
    n = type(n)
    if n < a:
        return a
    if n > b:
        return b
    return n


class Settings:
    def __init__(self):
        self.special_thresholds = {
            'white': 0.8,
            'black': 0.2,
            'gray': 0.2,
        }

        # Default thresholds adapted from:
        # https://e-reports-ext.llnl.gov/pdf/309492.pdf
        self.color_thresholds = [
            10, 20, 40, 50, 85, 90, 175, 185, 265, 275, 310, 320, 335, 350
        ]

        self.csv_output_fields = [
            'width', 'height',
            'white%', 'black%', 'gray%',
            'red%', 'orange%', 'yellow%', 'green%', 'blue%', 'purple%', 'pink%',
            'avg_h', 'avg_s', 'avg_l', 'stddev_h', 'stddev_s', 'stddev_l',
            'avg_sobel', 'opaque_pixels', 'opacity%',
        ]

        self.lang = 'en'

        self.output_images = [
            'source', 'colors', 'sobel', 'opacity', 'montage',
        ]

        self.special_display_colors = [
            from_hex('#ffffff'),
            from_hex('#7f7f7f'),
            from_hex('#000000'),
        ]
        self.main_display_colors = [
            from_hex('#ff0000'),
            from_hex('#ff7f00'),
            from_hex('#ffff00'),
            from_hex('#00ff00'),
            from_hex('#0000ff'),
            from_hex('#ff00ff'),
            from_hex('#ff007f'),
        ]
        self.transition_display_colors = [
            from_hex('#7f0000'),
            from_hex('#7f3f00'),
            from_hex('#7f7f00'),
            from_hex('#007f7f'),
            from_hex('#00007f'),
            from_hex('#7f007f'),
            from_hex('#7f003f'),
        ]

    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, value):
        self.field_names = FIELD_NAMES[value]
        self._lang = value

    def to_dict(self):
        result = collections.OrderedDict()
        result['version'] = 2

        tr = result['thresholds'] = collections.OrderedDict()
        tr['color'] = self.color_thresholds
        tr['special'] = collections.OrderedDict(
            (k, self.special_thresholds[k])
            for k in SPECIAL_NAMES
            if k in self.special_thresholds)

        dc = result['display_colors'] = collections.OrderedDict()
        dc['main'] = [to_hex(c) for c in self.main_display_colors]
        dc['transition'] = [to_hex(c) for c in self.transition_display_colors]
        dc['special'] = [to_hex(c) for c in self.special_display_colors]

        out = result['output'] = collections.OrderedDict()
        out['csv_fields'] = self.csv_output_fields
        out['images'] = self.output_images

        result['lang'] = self.lang
        return result

    def from_dict(self, dct):
        if dct.get('version', 2) != 2:
            raise ValueError('wrong data version')

        tr = dct.get('thresholds')
        if tr:
            color = tr.get('color')
            if color:
                color = list(color)
                if len(color) != len(self.color_thresholds):
                    raise ValueError('tresholds/color: wrong size of list')
                self.color_thresholds = [clamp(c, int, 0, 360) for c in color]
            special = tr.get('special')
            if special:
                sspt = self.special_thresholds
                for key in sspt:
                    value = special.get(key)
                    if value is not None:
                        sspt[key] = clamp(value, float, 0, 1)

        dc = dct.get('display_colors')
        if dc:
            for name, lst in (
                    ('main', self.main_display_colors),
                    ('transition', self.transition_display_colors),
                    ('special', self.special_display_colors),
                    ):
                source = dc.get(name)
                if source:
                    if len(source) > len(lst):
                        template = 'display_colors/{}: wrong size of list'
                        raise ValueError(template.format(name))
                    for i, (hexcolor, prev) in enumerate(zip(source, lst)):
                        lst[i] = from_hex(hexcolor)

        out = dct.get('output')
        if out:
            csvf = out.get('csv_fields')
            if csvf is not None:
                csvf = list(str(f) for f in csvf if f in FIELD_NAMES['en'])
                if csvf:
                    self.csv_output_fields = csvf
            imgs = out.get('images')
            if imgs is not None:
                imgs = list(str(f) for f in imgs if f in IMAGE_NAMES)
                if imgs:
                    self.output_images = imgs

        lang = dct.get('lang')
        if lang is not None and lang in FIELD_NAMES:
            self.lang = lang

    def save_to(self, f):
        representation = self.to_dict()
        json.dump(representation, f, indent=4, ensure_ascii=False)
        f.write('\n')

    @classmethod
    def load_from(cls, f):
        dct = json.load(f)
        result = cls()
        result.from_dict(dct)
        return result
