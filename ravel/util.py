#!/usr/bin/env python

import os
import sys

def _install_path():
    path = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(path, ".."))

def libpath(path):
    return os.path.normpath(
        os.path.join(_install_path(), path))

def append_path(path):
    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = ""

    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path

    if path is None or path == "":
        path = "."

    if path not in sys.path:
        sys.path.append(path)
