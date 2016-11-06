COLOR_NAMES = 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink'
SPECIAL_NAMES = 'white', 'gray', 'black', 'colorful'


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
