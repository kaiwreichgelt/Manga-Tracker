"""Double-click this to open the tracker.

The .pyw extension tells Windows to run it without a console window. The real
code is in gui.py, which stays importable so it can be tested.
"""

import os
import sys

# Double-clicking can start the app from any working directory, and the library
# file is looked up relative to this script, so pin both down.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

import gui

gui.main()
