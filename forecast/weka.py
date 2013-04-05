import commands
import os

from process import Process

WEKA_JAR_PATH = "%s/weka/weka-3-6-9/weka.jar" % os.getcwd()
WEKA_RUN_COMMAND = "java -Xmx1024m -cp %(classpath)s weka.classifiers.%(classifier)s -t \"%(input)s\" -no-cv -split-percentage %(split)s -preserve-order -i -k -v %(classifier_flags)s"

DEFAULT_SPLIT_PERCENT = 90

class WekaRunner:

    class ClassifierConfig:

        def __init__(self, classifier, classifier_flags):
            self.classifier = classifier
            self.classifier_flags = classifier_flags

    J48 = ClassifierConfig("trees.J48", "-C 0.25 -M 2")

    def run(self, classifier_config, input_file, split_percent=DEFAULT_SPLIT_PERCENT):
        weka_command = WEKA_RUN_COMMAND % {
                "input": input_file,
                "classifier": classifier_config.classifier,
                "classifier_flags": classifier_config.classifier_flags,
                "split": split_percent,
                "classpath": WEKA_JAR_PATH,
            }
        with Process("Running Weka: '%s'" % weka_command):
            output = commands.getoutput(weka_command)
        return output
