from glob import glob
import os

PARTIES_PATTERN = "parties/*.arff"
MEMBERS_PATTERN = "members/*.arff"
NOWC_FILE = ".nowc.arff"

files = glob(PARTIES_PATTERN) + glob(MEMBERS_PATTERN)
for f in files:
  f_nowc = f.replace(".arff", NOWC_FILE)
  if os.path.isfile(f_nowc):
    continue

  print "%s -> %s" % (f, f_nowc)
  content = file(f, "r").read()
  content = content.replace("?", "0")
  file(f_nowc, "w").write(content)
