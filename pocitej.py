# Encoding: UTF-8

from __future__ import division

import os
import csv

from PIL import Image
import numpy

white_threshold = 0.8
black_threshold = 0.2
gray_threshold = 0.2

report_values = (
        ('filename', 'Jméno souboru'),
        ('bbox_width', 'Šířka'),
        ('bbox_height', 'Výška'),
        ('p_white', '% Bílá'),
        ('p_black', '% Černá'),
        ('p_gray', '% Šedá'),
        ('p_red', '% Červená'),
        ('p_orange', '% Oranžová'),
        ('p_yellow', '% Žlutá'),
        ('p_green', '% Zelená'),
        ('p_blue', '% Modrá'),
        ('p_purple', '% Fialová'),
        ('p_pink', '% Růžová'),
        ('avg_h', 'Prům. H'),
        ('avg_s', 'Prům. S'),
        ('avg_l', 'Prům. L'),
        ('stddev_h', 'Směr. odch. H'),
        ('stddev_s', 'Směr. odch. S'),
        ('stddev_l', 'Směr. odch. L'),
        ('error', 'Chyba programu'),
    )

and_ = numpy.logical_and
or_ = numpy.logical_or
not_ = numpy.logical_not

def main(basedir, outfilename):
    # Open file
    out = csv.writer(open(outfilename, 'w'))
    # Write header
    out.writerow([val[1] for val in report_values])

    # Get list of filenames, sort alphabetically for better sense of progress
    filenames = os.listdir(basedir)
    filenames.sort(key=str.lower)
    # Total number of files
    total = len(filenames)

    # Iterate through files...
    for i, filename in enumerate(filenames):
        try:
            error = ''
            print "%4d/%4d - %s" % (i, total, filename)
            # Open image
            path = os.path.join(basedir, filename)
            image = Image.open(path)
            # RGBA
            image = image.convert('RGBA')
            # Crop
            bbox = image.getbbox()
            bbox_x1, bbox_y1, bbox_x2, bbox_y2 = bbox
            bbox_width = bbox_x2 - bbox_x1
            bbox_height = bbox_y2 - bbox_y1
            if not bbox:
                raise AssertionError('Empty image')
            image = image.crop(bbox)
            # Get individual pixels
            arr = numpy.array(image)
            pixels = numpy.vstack(arr) / 256.
            # Prepare matrices for red, green, blue, alpha
            rgb = pixels[:, :3]
            r = pixels[:, 0]
            g = pixels[:, 1]
            b = pixels[:, 2]
            a = pixels[:, 3]
            # Conversion to HSL: see [http://en.wikipedia.org/wiki/HSL_and_HSV]
            # Get min/max RGB, and min-max, for each pixel
            c_max = numpy.amax(rgb, 1)
            c_min = numpy.amin(rgb, 1)
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

            # Now for colors: get boolean mask for white, black, grey pixels
            white = (lum > white_threshold) * a
            black = (lum < black_threshold) * a
            gray = and_(not_(or_(white, black)), sat < gray_threshold) * a
            # The other pixels meaningful hue
            colorful = not_(or_(or_(white, black), gray))
            # Get boolean mask for each color, use intervals from
            # [https://e-reports-ext.llnl.gov/pdf/309492.pdf]
            red = and_(colorful, or_(hue < 20, hue > 335)) * a
            orange = and_(colorful, and_(10 < hue, hue < 50)) * a
            yellow = and_(colorful, and_(40 < hue, hue < 90)) * a
            green = and_(colorful, and_(85 < hue, hue < 185)) * a
            blue = and_(colorful, and_(175 < hue, hue < 275)) * a
            purple = and_(colorful, and_(265 < hue, hue < 320)) * a
            pink = and_(colorful, and_(310 < hue, hue < 350)) * a
            # Divide by total number of opaque pixels (and *100) to get percentages
            # of pixels with given color
            num_pixels = numpy.sum(a)
            color_percentages = numpy.sum([white, black, gray, red, orange, yellow, green, blue, purple, pink] / num_pixels * 100, 1)
            p_white, p_black, p_gray, p_red, p_orange, p_yellow, p_green, p_blue, p_purple, p_pink = color_percentages

            # Averages for saturation and lightness are easy
            avg_s, avg_l = numpy.average([sat, lum], 1, weights=a)
            stddev_s = weighted_std(sat, a, avg_s)
            stddev_l = weighted_std(lum, a, avg_l)
            # But hue is an angle, so we need to take the average of
            # corresponding unit vectors [http://stackoverflow.com/questions/491738]
            # And also we need to weight hue according to saturation/luminance
            hue_weight = sat * (1 - 2 * numpy.abs(lum - 0.5) % 1) * a
            hue_weight = colorful * a
            if sum(hue_weight):
                hue_radians = hue / 180 * numpy.pi
                unit_vectors = numpy.array([numpy.sin(hue_radians), numpy.cos(hue_radians)])
                avg_hue_vector = numpy.average(unit_vectors, 1, weights=hue_weight)
                avg_hue_rad = numpy.arctan2(*avg_hue_vector)
                avg_hue = (avg_hue_rad / numpy.pi * 180) % 360
                avg_h = avg_hue
                # Then to compute hue's std. deviation, normalize it into interval
                # [0, 360] so that the average is roughly at 180°
                hue_normalized = (hue - avg_hue + 180) % 360
                hue_norm_avg = numpy.average(hue_normalized, weights=hue_weight)
                stddev_h = weighted_std(hue_normalized, hue_weight, hue_norm_avg)
            else:
                avg_h = avg_hue = stddev_h = numpy.nan

            # Write it all out!
            loc = locals()
            out.writerow([loc[val[0]] for val in report_values])
            print ' ' * 11, 'OK'
        except Exception, e:
            error = "%s: %s" % (type(e).__name__, e)
            loc = dict(filename=filename, error=error)
            out.writerow([loc.get(val[0], '') for val in report_values])
            print ' ' * 11, 'Chyba:', error
            import traceback
            print traceback.format_exc()

def weighted_std(values, weights, mean):
    """Weighted standard deviation given values, weights, and the values' weighted mean
    Inspired by [http://stackoverflow.com/questions/2413522/weighted-std-in-numpy]
    ("Fast and numerically precise")
    """
    variance = numpy.dot(weights, (values-mean)**2) / numpy.sum(weights)
    return numpy.sqrt(variance)

if __name__ == '__main__':
    import sys
    try:
        basedir = sys.argv[1]
    except IndexError:
        basedir = 'obrazky'
    try:
        outfilename = sys.argv[2]
    except IndexError:
        outfilename = 'obrazky.csv'
    main(basedir, outfilename)
