from forecast.models import VoteMemberDecision
from search.words.contexted_words import ContextedBagOfWords

def Build(member_id):
  contexts = {'FOR': [], 'AGAINST': [], 'ABSTAIN': []}
  decisions = VoteMemberDecision.objects.filter(member_id=member_id)
  for decision in decisions:
    contexts[decision.decision].append(decision.vote.title)

  bag_of_words = ContextedBagOfWords()
  for context in contexts:
    bag_of_words.AddContext(context, contexts[context])
  bag_of_words.Disjoin()

  return bag_of_words
