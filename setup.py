#!/usr/bin/python

import os

cwd = os.getcwd()
with open(cwd + '/oknesset/settings-template.py', 'r') as template:
  settings = template.read()
  settings = settings.replace('{PATH}', cwd)
  with open(cwd + '/oknesset/settings.py', 'w') as actual:
    actual.write(settings)
