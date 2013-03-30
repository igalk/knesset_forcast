from forecast.models import VoteMemberDecision
from itertools import chain
from search.words.contexted_words import ContextedBagOfWords

def Build(**kwargs):
  member = kwargs.get("member", None)
  party = kwargs.get("party", None)
  if (member and party) or (not member and not party):
    raise Exception("Exactly one of member or party must be set")
  contexts = {'FOR': [], 'AGAINST': [], 'ABSTAIN': []}
  if member:
    decisions = VoteMemberDecision.objects.filter(member_id=member.id)
  else:
    decisions = list(chain.from_iterable(
      [VoteMemberDecision.objects.filter(member_id=member.id)
       for member in party.member_set.all()]))

  for decision in decisions:
    contexts[decision.decision].append(decision.vote.title)

  bag_of_words = ContextedBagOfWords()
  for context in contexts:
    bag_of_words.AddContext(context, contexts[context])
  bag_of_words.Disjoin()

  return bag_of_words
