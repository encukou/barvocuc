import collections

from PIL import Image
import numpy
from scipy import ndimage

from .settings import Settings, COLOR_NAMES, SPECIAL_NAMES

and_ = numpy.logical_and
or_ = numpy.logical_or
not_ = numpy.logical_not


class ImageAnalyzer:
    def __init__(self, image, *, settings=None, rgba_array=None):
        if settings is None:
            settings = Settings()
        self.settings = settings

        self.arrays = _FillDict(self._array_factories, self)
        self.results = _FillDict(self._result_factories, self)
        self.images = _FillDict(self._image_factories, self)

        if rgba_array is None:
            if not isinstance(image, Image.Image):
                image = Image.open(image)

            # RGBA
            image = image.convert('RGBA')

            # Get individual pixels
            if settings.model_version >= 2:
                divisor = 255.
            else:
                divisor = 256.
            self.arrays['rgba'] = arr = numpy.array(image) / divisor
        else:
            self.arrays['rgba'] = arr = rgba_array

        self.results['width'] = self.width = self.arrays['rgba'].shape[1]
        self.results['height'] = self.height = self.arrays['rgba'].shape[0]

    def clone(self, settings=None):
        return ImageAnalyzer(image=None, rgba_array=self.arrays['rgba'],
                             settings=settings or self.settings)

    _array_factories = {}
    _result_factories = {}
    _image_factories = {}

    def _resultmaker(attr_name, factories):
        def _maker(*names):
            def _decorator(func):
                def _decorated(self, *args, **kwargs):
                    results = func(self, *args, **kwargs)
                    for result, name in zip(results, names):
                        getattr(self, attr_name)[name] = result
                    return results
                for name in names:
                    factories[name] = _decorated
                return _decorated
            return _decorator
        return _maker

    _make_arrays = _resultmaker('arrays', _array_factories)
    _make_results = _resultmaker('results', _result_factories)

    def _make_images(*names,
                     _resultmaker=_resultmaker,
                     _image_factories=_image_factories,
                     _make_arrays=_make_arrays):
        _imgmaker = _resultmaker('images', _image_factories)(*names)
        _arrmaker = _make_arrays(*('img_' + n for n in names))
        def _decorator(func):
            _arrmaker(func)
            def _mkimage(self, name):
                array = self.arrays['img_' + name]
                img = Image.fromarray(numpy.uint8(array * 255))
                img.format = 'RGBA'
                return img
            def _mkresults(self, *args, **kwargs):
                return tuple(_mkimage(self, name) for name in names)
            return _imgmaker(_mkresults)
        return _decorator

    @_make_arrays('r', 'g', 'b', 'a', 'h', 's', 'l')
    def make_rgbahsl(self):
        """Extract RGB channels, and compute HSL channels"""
        pixels = self.arrays['rgba']
        rgb = self.arrays['rgba'][..., :3]
        r = pixels[..., 0]
        g = pixels[..., 1]
        b = pixels[..., 2]
        a = pixels[..., 3]

        # Conversion to HSL: see [http://en.wikipedia.org/wiki/HSL_and_HSV]
        # Get min/max RGB, and min-max, for each pixel
        c_max = numpy.amax(rgb, -1)
        c_min = numpy.amin(rgb, -1)
        c_diff = c_max - c_min
        # Compute hue
        hue = numpy.select(
                [c_max == c_min, c_max == r, c_max == g, c_max == b],
                [
                        0,
                        60.0 * ((g - b) / c_diff) + 360,
                        60.0 * ((b - r) / c_diff) + 120,
                        60.0 * ((r - g) / c_diff) + 240.0,
                    ]
            )
        hue %= 360  # Normalize angle

        # Get luminance & stauration
        lum = 0.5 * (c_max + c_min)
        sat = numpy.select(
                [c_max == c_min, lum < 0.5, lum >= 0.5],
                [
                        0,
                        (c_max - c_min) / (2.0 * lum),
                        (c_max - c_min) / (2.0 - (2.0 * lum)),
                    ]
            )
        return r, g, b, a, hue, sat, lum

    @_make_arrays('sobel_x', 'sobel_y', 'sobel')
    def make_sobel(self):
        """Find edges using the Sobel filter"""
        luminance = self.arrays['l']

        sx = ndimage.sobel(luminance, axis=0, mode='nearest')
        sy = ndimage.sobel(luminance, axis=1, mode='nearest')
        sob = numpy.hypot(sx, sy)
        return sx, sy, sob

    @_make_arrays('white', 'gray', 'black', 'colorful', 'opacity')
    def make_special_masks(self):
        """Make Boolean masks for "special" colors"""
        lum = self.arrays['l']
        sat = self.arrays['s']
        a = self.arrays['a']
        thresholds = self.settings.special_thresholds
        white = and_(lum > thresholds['white'], a)
        black = and_(lum < thresholds['black'], a)
        gray = and_(and_(not_(or_(white, black)), sat < thresholds['gray']), a)
        # The other pixels have meaningful hue
        colorful = not_(or_(or_(white, black), gray))

        opacity = a
        return white, gray, black, colorful, opacity

    @_make_arrays(*COLOR_NAMES)
    def make_color_masks(self):
        """Make Boolean masks for regular colors"""
        hue = self.arrays['h']
        a = self.arrays['a']
        colorful = self.arrays['colorful']
        thresholds = self.settings.color_thresholds
        num_thresholds = len(thresholds)

        results = []
        for i, name in enumerate(COLOR_NAMES):
            start = i * 2 - 2
            end = i * 2 + 1
            if start < 0:
                op = or_
            else:
                op = and_
            op1 = (thresholds[start % num_thresholds] < hue)
            op2 = (hue <= thresholds[end % num_thresholds])
            result = and_(colorful, op(op1, op2))
            results.append(result)

        self._color_masks = tuple(results)
        return results

    @property
    def color_masks(self):
        try:
            return self._color_masks
        except AttributeError:
            self.make_color_masks()
            return self._color_masks

    @property
    def special_masks(self):
        return tuple(self.arrays[n] for n in SPECIAL_NAMES)

    @_make_results('opaque_pixels', 'opacity', 'opacity%')
    def make_opacity_results(self):
        a = self.arrays['a']
        num_opaque_pixels = numpy.sum(a)
        opacity = num_opaque_pixels / (a.shape[0] * a.shape[1])
        return num_opaque_pixels, opacity, opacity * 100

    for name in COLOR_NAMES + SPECIAL_NAMES:

        if name != 'opacity':
            @_make_results(name, name + '%')
            def make_color_ratios(self, _name=name):
                a = self.arrays['a']
                opx = self.results['opaque_pixels']
                color = self.arrays[_name]
                result = numpy.sum(color * a) / opx
                return result, result * 100

    for name in 'r', 'g', 'b', 's', 'l', 'sobel', 'sobel_x', 'sobel_y':

        @_make_results('avg_' + name, 'stddev_' + name)
        def _make_linear_stats(self, _name=name):
            a = self.arrays['a']
            a = a.flatten()
            src = self.arrays[_name].flatten()
            avg = numpy.average(src, weights=a)
            stddev = weighted_stddev(src, weights=a, mean=avg)
            return avg, stddev

    @_make_results('avg_h', 'stddev_h')
    def make_hue_stats(self):
        # Hue is an angle, so we need to take the average of
        # corresponding unit vectors
        # [http://stackoverflow.com/questions/491738]
        # And also we need to weight hue according to saturation/luminance
        a = self.arrays['a']
        hue = self.arrays['h']
        sat = self.arrays['s']
        lum = self.arrays['l']
        colorful = self.arrays['colorful']
        hue_weight = sat * (1 - 2 * numpy.abs(lum - 0.5) % 1) * a
        hue_weight = colorful * a

        if numpy.sum(hue_weight).any():
            hue_radians = hue / 180 * numpy.pi

            hue_radians = hue_radians.flatten()
            hue_weight = hue_weight.flatten()

            unit_vectors = numpy.array([numpy.sin(hue_radians),
                                        numpy.cos(hue_radians)])
            avg_hue_vector = numpy.sum(unit_vectors * hue_weight, axis=1)
            avg_hue_rad = numpy.arctan2(*avg_hue_vector)
            avg_hue = (avg_hue_rad / numpy.pi * 180) % 360
            avg_h = avg_hue
            # Then to compute hue's std. deviation, normalize it into interval
            # [0, 360] so that the average is roughly at 180°
            hue_normalized = (hue.flatten() - avg_hue + 180) % 360
            hue_norm_avg = numpy.average(hue_normalized, weights=hue_weight)
            stddev_h = weighted_stddev(hue_normalized,
                                       weights=hue_weight, mean=hue_norm_avg)
        else:
            avg_h = avg_hue = stddev_h = numpy.nan

        return avg_h, stddev_h

    @property
    def csv_results(self):
        return {n: self.results[n] for n in self.settings.csv_output_fields}

    @_make_images('source')
    def make_source_image(self):
        rgba = self.arrays['rgba']
        return [rgba]

    @_make_images('colors')
    def make_source_image(self):
        result = numpy.zeros((self.height, self.width, 4), dtype=float)

        base_colors = self.color_masks
        b = lambda a: numpy.array(a, dtype=bool)
        masks = list(self.special_masks[:3])
        for color in base_colors:
            masks.append(color)
        for i, color in enumerate(base_colors):
            next = base_colors[(i + 1) % len(base_colors)]
            masks.append(and_(color, next))

        colors = (self.settings.special_display_colors
                  + self.settings.main_display_colors
                  +self.settings.transition_display_colors)

        for mask, color in zip(masks, colors):
            result[mask, :3] = color

        result[..., 3] = self.arrays['a']
        return [result]

    @_make_images('sobel')
    def make_sobel_image(self):
        def normalize(arr):
            abs_arr = abs(arr)
            return abs_arr / numpy.max(abs_arr)
        result = numpy.dstack((
            normalize(self.arrays['sobel']) ** 2,
            normalize(self.arrays['sobel']),
            normalize(self.arrays['sobel']) ** 0.5,
            self.arrays['a'],
        ))
        return [result]

    @_make_images('opacity')
    def make_sobel_image(self):
        result = numpy.dstack((
            1-self.arrays['a'],
            1-self.arrays['a'],
            1-self.arrays['a'],
            numpy.ones((self.height, self.width)),
        ))
        return [result]

    @_make_images('montage')
    def make_sobel_image(self):
        arrs = self.arrays
        result = numpy.vstack((
            numpy.hstack((arrs['img_source'], arrs['img_colors'])),
            numpy.hstack((arrs['img_sobel'], arrs['img_opacity'])),
        ))
        return [result]


def weighted_stddev(values, *, weights, mean):
    """Weighted standard deviation given values, weights, and the weighted mean
    Inspired by
    [http://stackoverflow.com/questions/2413522/weighted-std-in-numpy]
    ("Fast and numerically precise")
    """
    variance = numpy.dot(weights, (values-mean)**2) / numpy.sum(weights)
    return numpy.sqrt(variance)


class _FillDict(collections.abc.MutableMapping):
    def __init__(self, factories, *args):
        self._factories = dict(factories)
        self._args = args
        self._results = {}

    def __getitem__(self, item):
        try:
            return self._results[item]
        except KeyError:
            factory = self._factories[item]
            factory(*self._args)
            return self._results[item]

    def __iter__(self):
        return iter(self._factories)

    def __len__(self):
        return len(self._factories)

    def __setitem__(self, item, value):
        self._results[item] = value

    def __delitem__(self, item, value):
        del self._results[item]
