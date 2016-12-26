from setuptools import setup, find_packages
import sys


setup_args = dict(
    name='barvocuc',
    version='2.0b2',
    description='Software for Analysis of Color Images',
    #long_description="TODO",
    author='Petr Viktorin',
    author_email='encukou@gmail.com',
    license='GPL v3+',
    url='https://github.com/encukou/barvocuc',
    packages=find_packages(),
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        ],
    install_requires=[
        'Pillow',
        'Numpy',
        'Scipy',
        'Click',
        ],
    extras_require={
        'gui':  ["PyQT5"],      # GUI support
        'oldconf': ["PyYAML"],  # Old config file support
        'test': ["pytest"],     # Test suite
    },
    package_data={
        'barvocuc': [
            'COPYING.html',
            'ui/*',
            'translations/*',
            'media/*',
        ],
    },
    zip_safe=False,
)

if sys.platform == 'win32':
    # py2exe arguments
    setup_args.update(dict(
        zipfile=None,
        console=['gui.py'],
    ))
    setup_args['install_requires'].extend(['PyQT5', 'PyYAML'])


if __name__ == '__main__':
    setup(**setup_args)
