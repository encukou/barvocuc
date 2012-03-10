
white_threshold = 0.8
black_threshold = 0.2
gray_threshold = 0.2

orange_start = 10
red_end = 20
yellow_start = 40
orange_end = 50
green_start = 85
yellow_end = 90
blue_start = 175
green_end = 185
purple_start = 265
blue_end = 275
pink_start = 310
purple_end = 320
red_start = 335
pink_end = 350

RED = 1, 0, 0
RED_ORG = 0.5, 0, 0
ORG = 1, 0.5, 0
ORG_YLW = 0.5, 0.25, 0
YLW = 1, 1, 0
YLW_GRN = 0.5, 0.5, 0
GRN = 0, 1, 0
GRN_BLU = 0, 0.5, 0.5
BLU = 0, 0, 1
BLU_PUR = 0, 0, 0.5
PUR = 1, 0, 1
PUR_PNK = 0.5, 0, 0.5
PNK = 1, 0, 0.5
PNK_RED = 0.5, 0, 0.25

WHI = 1, 1, 1
BLK = 0, 0, 0
GRY = .5, .5, .5

class Settings(object):
    def __init__(self):
        self.fix()

    def fix(self):
        self._setdefault('colors', RED, RED_ORG, ORG, ORG_YLW, YLW, YLW_GRN, GRN, GRN_BLU, BLU, BLU_PUR, PUR, PUR_PNK, PNK, PNK_RED)
        self._setdefault('spc_colors', WHI, BLK, GRY)
        self._setdefault('thresholds', 10, 20, 40, 50, 85, 90, 175, 185, 265, 275, 310, 320, 335, 350)
        self._setdefault('spc_thresholds', 80, 20, 20)

    def _setdefault(self, name, *defaults):
        """Fix list attribute after loading - make sure it's a list, and add missing values from defaults"""
        attr = getattr(self, name, [])
        setattr(self, name, attr)
        attr.extend(defaults[len(attr):])
