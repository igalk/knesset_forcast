import commands
import os

from process import Process

WEKA_JAR_PATH = "%s/weka/weka-3-6-9/weka.jar" % os.getcwd()
WEKA_RUN_COMMAND = (
    "java -Xmx1024m -cp %(classpath)s " +
    "weka.classifiers.%(classifier)s " +
    "-t \"%(input)s\" -split-percentage %(split)s -preserve-order " +
    "-i -k -v %(classifier_flags)s"
  )
WEKA_FILTER_RUN_COMMAND = (
    "java -Xmx1024m -cp %(classpath)s " +
    "weka.classifiers.meta.FilteredClassifier " +
    "-F \"weka.filters.unsupervised.attribute.Remove -R %(ignore_features)s\" " +
    "-t \"%(input)s\" -split-percentage %(split)s -preserve-order -i -k -v " +
    "-W weka.classifiers.%(classifier)s -- %(classifier_flags)s"
  )

DEFAULT_SPLIT_PERCENT = 90

class WekaRunner:

    class Output:
        
        def __init__(self, raw_output, correct_percent, confusion_matrix, classifier, error):
            self.raw_output = raw_output
            self.correct_percent = correct_percent
            self.confusion_matrix = confusion_matrix
            self.classifier = classifier
            self.error = error

    class ClassifierConfig:

        def __init__(self, name, classifier, classifier_flags):
            self.name = name
            self.classifier = classifier
            self.classifier_flags = classifier_flags

    CONFIGS = {
        "ID3"         : ClassifierConfig("ID3"         , "trees.Id3"         , ""               ),
        "J48-0.25"    : ClassifierConfig("J48-0.25"    , "trees.J48"         , "-C 0.25 -M 2"   ),
        "J48-0.5"     : ClassifierConfig("J48-0.5"     , "trees.J48"         , "-C 0.5 -M 2"    ),
        "J48-0.75"    : ClassifierConfig("J48-0.75"    , "trees.J48"         , "-C 0.75 -M 2"   ),
        "RandomForest": ClassifierConfig("RandomForest", "trees.RandomForest", "-I 10 -K 0 -S 1"),
        "NaiveBayes"  : ClassifierConfig("NaiveBayes"  , "bayes.NaiveBayes"  , ""               ),
        "IBk-KNN"     : ClassifierConfig("IBk-KNN"     , "lazy.IBk"          ,
                                         '-K 1 -W 0 -A "weka.core.neighboursearch.KDTree -A ' +
                                         '\\"weka.core.EuclideanDistance -R first-last\\" -S ' +
                                         'weka.core.neighboursearch.kdtrees.SlidingMidPointOfWidestSide ' +
                                         '-W 0.01 -L 40 -N'),
    }
    ALL_SPLITS = [66, 70, 75, 80, 85, 90, 95]

    def run(self, classifier_config, input_file, split_percent=DEFAULT_SPLIT_PERCENT,
            features_to_ignore=None):
        weka_command = WEKA_FILTER_RUN_COMMAND
        if not features_to_ignore:
            weka_command = WEKA_RUN_COMMAND
            features_to_ignore = []
        
        def range_to_string(t):
            try:
                return "-".join([str(i) for i in t])
            except:
                return str(t)
        features_to_ignore = ",".join([range_to_string(t) for t in features_to_ignore])

        weka_command = weka_command % {
                "input": input_file,
                "classifier": classifier_config.classifier,
                "classifier_flags": classifier_config.classifier_flags,
                "split": split_percent,
                "ignore_features": features_to_ignore,
                "classpath": WEKA_JAR_PATH,
            }
        with Process("Running Weka: '%s'" % weka_command):
            output_str = commands.getoutput(weka_command)
        with Process("Parsing Weka Output"):
            output = self._parseOutput(output_str, classifier_config)
        return output

    def _parseOutput(self, output_str, classifier_config):
        raw_str = output_str

        try:
            # Split the output into sections to process.
            classifier_section, output_str = output_str.split("=== Error on test split ===")
            error_section, confusion_section = output_str.split("=== Confusion Matrix ===")

            # Process the classifier section.
            classifier_section = classifier_section.strip()

            # Process the error section.
            correct_percent = float(error_section.strip().split("%")[0].strip().split()[-1])

            # Process the confusion section.
            confusion_matrix = confusion_section.strip()

            error = False
        except:
            classifier_section = ""
            confusion_matrix = ""
            correct_percent = -1.0
            error = True

        return self.Output(raw_str, correct_percent, confusion_matrix,
                           classifier_section, error)
