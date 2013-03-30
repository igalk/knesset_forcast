from django.core.exceptions import ObjectDoesNotExist
from forecast.feature import *
from search.words.contexted_words import ContextedBagOfWords

class MemberBillFeaturesUtils:
  @staticmethod
  def ExtractClassification(member, bill):
    decisions = MajorityDecision()
    for vote in bill.vote_set.all():
      decision_set = vote.votememberdecision_set.filter(member_id=member.id)
      decision = decision_set and decision_set[0].decision or 'NO_SHOW'
      if vote.type == 'approval':
        return decision
      decisions.AddDecision(decision)
    return decisions.GetDecision()

class MemberProposedBillFeature(BooleanFeature):
  """Feature is True if the member was one of the proposers of the bill."""
  def __init__(self):
    Feature.__init__(self, "Member proposed the Bill")

  def Extract(self, member, bill):
    return (member in bill.proposing_members.all())

class MemberJoinedBillFeature(BooleanFeature):
  """Feature is True if the member was one of the joiners of the bill."""
  def __init__(self):
    Feature.__init__(self, "Member joined the Bill")

  def Extract(self, member, bill):
    return (member in bill.joining_members.all())

class MemberInBillProposingPartyFeature(BooleanFeature):
  """Feature is True if the member is in a party that proposed the bill."""
  def __init__(self):
    Feature.__init__(self, "Member in a Party that proposed the Bill")

  def Extract(self, member, bill):
    return (member.party in bill.ProposingParties())

class MemberInBillJoiningPartyFeature(BooleanFeature):
  """Feature is True if the member is in a party that joined the bill."""
  def __init__(self):
    Feature.__init__(self, "Member in a Party that joined the Bill")

  def Extract(self, member, bill):
    return (member.party in bill.JoiningParties())

class MemberInCoalitionFeature(BooleanFeature):
  """Feature is True if the member is in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Member in coalition")

  def Extract(self, member, bill):
    return member.party.is_in_coalition

# TODO(lagi): this is wrong, it doesn't do what's written in the documentation!!
class MemberSupportsBillAgendaFeature(BooleanFeature):
  """Feature is True if the member supports an agenda that the bill promotes."""
  def __init__(self):
    Feature.__init__(self, "Member supports an agenda that the bill promotes")

  def Extract(self, member, bill):
    decisions = MajorityDecision()
    for party_member in member.party.member_set.all():
      if member.id == party_member.id:
        continue
      decisions.AddDecision(
          MemberBillFeaturesUtils.ExtractClassification(party_member, bill))

    return decisions.GetDecision() == 'FOR'

class BillHasKeyWords(Feature):
  """Feature states a classification if the title of the bill contains a words that were unique to a specific category."""
  def __init__(self, bag_of_words):
    Feature.__init__(self, "States a category of classifications according to words in the title")
    self.bag_of_words = bag_of_words

  def Extract(self, member, bill):
    words = set()
    for vote in bill.vote_set.all():
      words = words.union(ContextedBagOfWords.ExtractWords(vote.title))

    counters = {context: len(words.intersection(self.bag_of_words.disjoin[context]))
                for context in self.bag_of_words.disjoin}
    non_zero_counters = sum([1 for c in counters.values() if c > 0])
    if non_zero_counters != 1:
      return 'NONE'
    for c in counters:
      if counters[c] > 0:
        return c

  def LegalValues(self):
    return ['FOR', 'AGAINST', 'ABSTAIN', 'NONE']

def MemberBillsFeatures(bag_of_words):
  if not bag_of_words:
    raise Exception("Bag of words can't be None")
  return [MemberProposedBillFeature(),
          MemberJoinedBillFeature(),
          MemberInBillProposingPartyFeature(),
          MemberInBillJoiningPartyFeature(),
          MemberInCoalitionFeature(),
          BillProposingPartyInCoalitionFeature(),
          BillJoiningPartyInCoalitionFeature(),
          BillProposingPartyInOpositionFeature(),
          BillJoiningPartyInOpositionFeature(),
          BillHasKeyWords(bag_of_words)]

class MemberBillsFeatureExtractor:
  def Extract(self, member, bills, features):
    feature_values = {}
    for bill in bills:
      values = []
      for feature in features:
        values.append(feature.Extract(member, bill))
      classification = MemberBillFeaturesUtils.ExtractClassification(member, bill)
      bill_date = max([vote.time for vote in bill.vote_set.all()])
      feature_values[bill.id] = tuple((tuple(values), classification, bill_date))

    return feature_values
