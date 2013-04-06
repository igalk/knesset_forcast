import glob
import os
import shutil

PATH_LOCATION = "/tmp/progress/"

class Progress:
  def __init__(self):
    self.count = 0
    self.names = {}

  def Reset(self):
    if os.path.exists(PATH_LOCATION):
      shutil.rmtree(PATH_LOCATION)
    os.mkdir(PATH_LOCATION)

  def GetProgresses(self):
    progresses = []
    for f in glob.glob(PATH_LOCATION + "*"):
      p = open(f, 'r').read().strip().split('\n')
      progress = [p[0]] + p[1].split('|')
      if len(p) > 2:
        progress += [p[2]]
      progresses += [progress]

    return progresses

  def WriteProgress(self, name, current, total, done=False):
    if name in self.names:
      index = self.names[name]
    else:
      index = self.count
      self.names[name] = index
      self.count += 1

    status = "%s\n%d|%d" % (name, current, total)
    if done:
      status += "\nDone"
    f = '0'*(4-len(str(index))) + str(index)
    open(PATH_LOCATION + f, "w").write(status)
