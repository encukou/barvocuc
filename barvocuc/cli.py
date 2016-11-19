import click

from .batch import generate_csv


@click.group()
def cli():
    pass


@cli.command()
@click.option('--output', '-o', type=click.File('w'), default='-')
@click.option('--outdir',
              type=click.Path(exists=False, file_okay=False, dir_okay=True,
                              resolve_path=True),
              )
@click.argument('path', type=click.Path(), nargs=-1)
def analyze(output, path, outdir):
    generate_csv(output, path, outdir=outdir)


@cli.command()
def gui():
    from .gui import main
    return main()
