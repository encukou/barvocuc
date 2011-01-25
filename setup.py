from distutils.core import setup

import py2exe


setup(
    zipfile = None,
    console=['gui.py'],
 excludes = ["pywin", "pywin.debugger", "pywin.debugger.dbgcon",
                "pywin.dialogs", "pywin.dialogs.list",
                "Tkconstants","Tkinter","tcl"
                ]
)