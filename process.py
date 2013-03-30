import sys

class Process:
  def __init__(self, message):
    self.message = message

  def __enter__(self):
    print ('%s ...' % self.message),
    sys.stdout.flush()

  def __exit__(self, type, value, traceback):
    print 'DONE'
