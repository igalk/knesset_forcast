from django.core.exceptions import ObjectDoesNotExist
from forecast.feature import *
from forecast.member_bills_feature_extractor import MemberBillFeaturesUtils
from search.words.contexted_words import ContextedBagOfWords

class PartyBillFeaturesUtils:
  @staticmethod
  def ExtractClassification(party, bill):
    decisions = MajorityDecision()
    for member in party.member_set.all():
      decisions.AddDecision(
          MemberBillFeaturesUtils.ExtractClassification(member, bill))
    return decisions.GetDecision() 

class PartyMemberProposedBillFeature(BooleanFeature):
  """Feature is True if a party member was one of the proposers of the bill."""
  def __init__(self):
    Feature.__init__(self, "Party member proposed the Bill")

  def Extract(self, party, bill):
    return len(set(bill.proposing_members.all()).intersection(
               set(party.member_set.all()))) > 0

class PartyMemberJoinedBillFeature(BooleanFeature):
  """Feature is True if a party member was one of the joiners of the bill."""
  def __init__(self):
    Feature.__init__(self, "Party member joined the Bill")

  def Extract(self, party, bill):
    return len(set(bill.joining_members.all()).intersection(
               set(party.member_set.all()))) > 0

class PartyInCoalitionFeature(BooleanFeature):
  """Feature is True if the party is in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Party in coalition")

  def Extract(self, party, bill):
    return party.is_in_coalition

#TODO (lagi): This doesn't do what's written in the documentation!!
class PartySupportsBillAgendaFeature(BooleanFeature):
  """Feature is True if the party supports an agenda that the bill promotes."""
  def __init__(self):
    Feature.__init__(self, "Party supports an agenda that the bill promotes")

  def Extract(self, party, bill):
    decisions = MajorityDecision()
    for party_member in party.member_set.all():
      decisions.AddDecision(
          MemberBillFeaturesUtils.ExtractClassification(party_member, bill))
    return decisions.GetDecision() == 'FOR'

class BillHasKeyWords(Feature):
  """
  Feature states a classification if the title of the bill contains a words
  that were unique to a specific category.
  """
  def __init__(self, bag_of_words):
    Feature.__init__(self,
        "States a category of classifications according to words in the title")
    self.bag_of_words = bag_of_words

  def Extract(self, party, bill):
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

def PartyBillsFeatures(bag_of_words):
  if not bag_of_words:
    raise Exception("Bag of words can't be None")
  return [PartyMemberProposedBillFeature(),
          PartyMemberJoinedBillFeature(),
          PartyInCoalitionFeature(),
          PartySupportsBillAgendaFeature(),
          BillHasKeyWords(bag_of_words)]

class PartyBillsFeatureExtractor:
  def Extract(self, party, bills, features):
    feature_values = {}
    for bill in bills:
      values = []
      for feature in features:
        values.append(feature.Extract(party, bill))
      classification = PartyBillFeaturesUtils.ExtractClassification(party, bill)
      feature_values[bill.id] = tuple((tuple(values), classification))

    return feature_values
