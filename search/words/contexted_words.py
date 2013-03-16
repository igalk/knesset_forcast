CHARS_TO_CLEAR = [str(i) for i in range(10)] + [',', '(', ')', '-', '"']

class ContextedBagOfWords:
  def __init__(self):
    self.words = {}

  @staticmethod
  def CleanWord(word):
    w = word
    for c in CHARS_TO_CLEAR:
      w = w.replace(c, '')
    return w

  @staticmethod
  def ExtractWords(text):
    words = set()
    raw_words = text.split(' ')
    for word in raw_words:
      words.add(ContextedBagOfWords.CleanWord(word))
    words -= set([''])
    return words

  def AddContext(self, context, texts):
    words = set()
    for text in texts:
      words = words.union(ContextedBagOfWords.ExtractWords(text))
    self.words[context] = words

  def Disjoin(self):
    self.disjoin = {}
    for context in self.words:
      self.disjoin[context] = set(self.words[context])
      for other_context in self.words:
        if other_context == context:
          continue
        self.disjoin[context] -= self.words[other_context]
