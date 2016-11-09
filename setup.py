from setuptools import setup, find_packages
import sys


setup_args = dict(
    name='barvocuc',
    version='2.0b1',
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
        #'PyQT5',       # Not readily installable via pip
        'PyYAML',
        'Pillow',
        'Numpy',
        'Scipy',
        'Click',
        ],
    zip_safe=False,
)

if sys.platform == 'win32':
    # py2exe arguments
    setup_args.update(dict(
        zipfile=None,
        console=['gui.py'],
        excludes=["pywin", "pywin.debugger", "pywin.debugger.dbgcon",
                  "pywin.dialogs", "pywin.dialogs.list",
                  "Tkconstants", "Tkinter", "tcl",
                  ]
    ))


setup(**setup_args)
