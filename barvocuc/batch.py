import os

from .analysis import ImageAnalyzer
import csv

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


def generate_csv(csv_file, paths, *, settings=None):
    if settings is None:
        settings = Settings()

    output_fields = settings.csv_output_fields

    writer = csv.writer(csv_file, lineterminator='\n')

    paths = sorted(generate_paths(paths))
    prefix = os.path.commonpath(paths)

    writer.writerow([
        settings.field_names[n]
        for n in ('filename', *settings.csv_output_fields, 'error')
        ])

    for path in paths:
        relpath = os.path.relpath(path, prefix)
        try:
            analyzer = ImageAnalyzer(path, settings=settings)
        except Exception as e:
            writer.writerow((relpath, *['' for _ in output_fields],
                             format_exc(e)))
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
            writer.writerow((
                relpath,
                *values,
                '; '.join(
                    '{} ({})'.format(msg, ','.join(fields))
                    for msg, fields in errors.items()
                    ),
                ))
