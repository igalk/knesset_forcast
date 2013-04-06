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

# Feature 1: Party<>Bill
class PartyMemberProposedBillFeature(BooleanFeature):
  """Feature is True if a party member was one of the proposers of the bill."""
  def __init__(self):
    Feature.__init__(self, "Party member proposed the Bill")

  def Extract(self, party, bill):
    return bool(set(bill.proposing_members.all()).intersection(
                set(party.member_set.all())))

# Feature 2: Party<>Bill
class PartyMemberSupportedBillFeature(BooleanFeature):
  """Feature is True if a party member was supporting the bill."""
  def __init__(self):
    Feature.__init__(self, "Party member supported the Bill")

  def Extract(self, party, bill):
    return bool(set(bill.joining_members.all()).intersection(
                set(party.member_set.all())))

# Feature 3: Party
class PartyInCoalitionFeature(BooleanFeature):
  """Feature is True if the party is in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Party in coalition")

  def Extract(self, party, bill):
    return party.is_in_coalition

# Feature 4
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

def PartyBillsFeatures(): #bag_of_words):
  # if not bag_of_words:
  #   raise Exception("Bag of words can't be None")
  return [PartyMemberProposedBillFeature(), # Feature 1
          PartyMemberSupportedBillFeature(), # Feature 2
          PartyInCoalitionFeature(), # Feature 3
          BillProposingPartyInCoalitionFeature(), # Feature 1 @feature.py
          BillSupportingPartyInCoalitionFeature(), # Feature 2 @feature.py
          BillProposingPartyInOppositionFeature(), # Feature 3 @feature.py
          BillSupportingPartyInOppositionFeature(), # Feature 4 @feature.py
          BillSupportingAgendaFeature(), # Feature 5 @feature.py
          BillHasTagFeature(), # Feature 6 @feature.py
          # BillHasKeyWords(bag_of_words), # Feature 4
         ]

class PartyBillsFeatureExtractor:
  def __init__(self, progress):
    self.progress = progress

  def Extract(self, party, bills, features):
    feature_values = {}
    self.progress.WriteProgress("Extracting features", 0, len(bills))

    for i, bill in enumerate(bills):
      self.progress.WriteProgress("Extracting features", i, len(bills))
      values = []
      for feature in features:
        if isinstance(feature, FeatureSet):
          values.extend(feature.Extract(party, bill))
        else:
          values.append(feature.Extract(party, bill))
      classification = PartyBillFeaturesUtils.ExtractClassification(party, bill)
      bill_date = max([vote.time for vote in bill.vote_set.all()])
      feature_values[bill.id] = tuple((tuple(values), classification, bill_date))

    self.progress.WriteProgress("Extracting features", len(bills), len(bills), True)
    return feature_values
