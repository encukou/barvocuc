COLOR_NAMES = 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink'
SPECIAL_NAMES = 'white', 'gray', 'black', 'colorful'

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
        'error': 'Chyba programu',
    },
}

for table in FIELD_NAMES.values():
    for ident in SPECIAL_NAMES + COLOR_NAMES:
        name = table.get(ident)
        if name:
            table.setdefault(ident + '%', '% ' + name)


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
            'avg_sobel',
        ]

        self.lang = 'en'


    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, value):
        self.field_names = FIELD_NAMES[value]
        self._lang = value
