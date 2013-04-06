class TestResults:

  def __init__(self):
    self.rows = [["\"ID\"", "\"Classifier\"", "\"% Training\"",
                  "\"Use Agendas\"", "\"Use Tags\"", "\"Use Coalition\"", "\"Use BOW\"",
                  "\"Use ?\"", "\"% Correct\""]]
    
  def addResult(self, member_id, classifier_config, split_percent,
                ignore_feature_sets, with_wildcards, output):
    row = ([member_id] + [classifier_config.name] + [split_percent] +
           [f for f in ignore_feature_sets] + [with_wildcards] +
           [output.correct_percent])
    row = [("\"%s\"" % c) for c in row]
    assert len(row) == len(self.rows[0])
    self.rows.append(row)

  def exportCSV(self, path):
    csv = file(path, "w")
    csv.write("".join([(",".join(row) + "\n") for row in self.rows]))
    csv.close()
