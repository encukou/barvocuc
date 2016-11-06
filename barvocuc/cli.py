import click

from .batch import generate_csv


@click.group()
def cli():
    print('g')


@cli.command()
@click.option('--output', '-o', type=click.File('w'), default='-')
@click.argument('path', type=click.Path(), nargs=-1)
def analyze(output, path):
    generate_csv(output, path)
