import os
import sys
import csv

from .analysis import ImageAnalyzer
from .settings import Settings


IMAGE_EXTENSIONS = '.png', '.jpg', '.jpeg', '.gif'


def generate_paths(paths):
    if isinstance(paths, str):
        raise TypeError('paths must not be a single string')

    for path in paths:
        if os.path.isdir(path):
            for subpath in os.listdir(path):
                if subpath.lower().endswith(IMAGE_EXTENSIONS):
                    yield os.path.abspath(os.path.join(path, subpath))
        else:
            yield os.path.abspath(path)


def format_exc(e):
    return '{}: {}'.format(type(e).__name__, e)


def generate_csv(csv_file, paths, *, settings=None, outdir=None):
    if settings is None:
        settings = Settings()

    if outdir is not None:
        outdir = os.path.abspath(outdir)
        os.makedirs(outdir, exist_ok=True)

    output_fields = settings.csv_output_fields

    writers = []
    if csv_file:
        writers.append(csv.writer(csv_file, lineterminator='\n'))
    if outdir:
        outfile = open(os.path.join(outdir, 'out.csv'), 'w', encoding='utf-8')
        writers.append(csv.writer(outfile, lineterminator='\n'))

    def writerow(row):
        row = tuple(row)
        for writer in writers:
            writer.writerow(row)

    paths = sorted(generate_paths(paths))
    prefix = os.path.commonpath(paths)

    writerow(
        settings.field_names[n]
        for n in ('filename', *settings.csv_output_fields, 'error'))

    for path in paths:
        relpath = os.path.relpath(path, prefix)
        try:
            analyzer = ImageAnalyzer(path, settings=settings)
        except Exception as e:
            writerow((relpath, *['' for _ in output_fields], format_exc(e)))
        else:
            values = []
            errors = {}
            for field in settings.csv_output_fields:
                try:
                    value = analyzer.results[field]
                except Exception as e:
                    value = ''
                    errors.setdefault(format_exc(e), []).append(field)
                values.append(str(value))
            writerow((
                relpath,
                *values,
                '; '.join(
                    '{} ({})'.format(msg, ','.join(fields))
                    for msg, fields in errors.items()
                    ),
                ))
            if outdir:
                for name in settings.output_images:
                    filename = os.path.join(outdir, name, relpath)
                    try:
                        image = analyzer.images[name]
                        os.makedirs(os.path.dirname(filename), exist_ok=True)
                        image.save(filename)
                    except Exception as e:
                        print('Error saving image "{}" to {}: {}'.format(
                            name, filename, format_exc(e)), file=sys.stderr)

    if outdir:
        outfile.close()
