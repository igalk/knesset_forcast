from forecast.models import *
from itertools import chain
from search.words.contexted_words import ContextedBagOfWords

def Build(**kwargs):
  member = kwargs.get("member", None)
  party = kwargs.get("party", None)
  cutoff = kwargs.get("cutoff", 1)
  progress = kwargs["progress"]

  if (member and party) or (not member and not party):
    raise Exception("Exactly one of member or party must be set")

  progress.WriteProgress("Compile bag of words", 1, 1)
  contexts = {'FOR': [], 'AGAINST': [], 'ABSTAIN': []}
  # Get only bills from the cutoff
  bills = [(bill, max([vote.time for vote in bill.vote_set.all()])) for bill in Bill.objects.all() if bill.vote_set.all()]
  bills.sort(key=lambda b: b[1])
  bills = bills[:int(cutoff*len(bills))]
  votes = list(chain.from_iterable([bill[0].vote_set.all() for bill in bills]))
  vote_decisions = set(chain.from_iterable([VoteMemberDecision.objects.filter(vote_id=vote.id) for vote in votes]))
  
  if member:
    decisions = set(VoteMemberDecision.objects.filter(member_id=member.id)).intersection(vote_decisions)
  else:
    decisions = set(chain.from_iterable(
      [VoteMemberDecision.objects.filter(member_id=member.id)
       for member in party.member_set.all()])).intersection(vote_decisions)

  for i, decision in enumerate(decisions):
    contexts[decision.decision].append(decision.vote.title)

  bag_of_words = ContextedBagOfWords()
  for context in contexts:
    bag_of_words.AddContext(context, contexts[context])
  bag_of_words.Disjoin()

  progress.WriteProgress("Compile bag of words", 1, 1, True)
  return bag_of_words
