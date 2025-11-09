"""
This file adds the parent dir to the search path for
Python modules.

In GH CI we set `PYTHONPATH` env var to the workspace root
which is equivalent to what we are doing here.

https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH
https://fortierq.github.io/python-import/
"""

from pathlib import Path
import sys
import os

if os.environ.get("CI") != "true":
    path_root = Path(__file__).parents[1]
    sys.path.append(str(path_root))
    # print("Added project parent to sys.path:", str(path_root))
