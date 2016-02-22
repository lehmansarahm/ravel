#!/usr/bin/env python

import os
import re
import sys

from log import logger

def libpath(path=None):
    install_path = os.path.dirname(os.path.abspath(__file__))
    install_path = os.path.normpath(
        os.path.join(install_path, ".."))

    if not path:
        return install_path

    return os.path.normpath(os.path.join(install_path, path))

def update_trigger_path(filename, path):
    if not os.path.isfile(filename):
        logger.warning("cannot find sql file %s", filename)
        return

    with open(filename, 'r') as f:
        lines = []
        content = f.read()

    newstr = "sys.path.append('{0}')".format(path)
    pattern = re.compile(r"sys.path.append\(\S+\)")
    content = re.sub(pattern, newstr, content)

    open(filename, 'w').write(content)

def append_path(path):
    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = ""

    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path

    if path is None or path == "":
        path = "."

    if path not in sys.path:
        sys.path.append(path)
