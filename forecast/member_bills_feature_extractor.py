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

# Feature 1: Member<>Bill
class MemberProposedBillFeature(BooleanFeature):
  """Feature is True if the member was one of the proposers of the bill."""
  def __init__(self):
    Feature.__init__(self, "Member proposed the bill")

  def Extract(self, member, bill):
    return (member in bill.proposing_members.all())

# Feature 2: Member<>Bill
class MemberSupportedBillFeature(BooleanFeature):
  """Feature is True if the member supported the bill."""
  def __init__(self):
    Feature.__init__(self, "Member supported the bill")

  def Extract(self, member, bill):
    return (member in bill.joining_members.all()) or (member in bill.proposing_members.all())

# Feature 3: Member<>Bill
class MemberInBillProposingPartyFeature(BooleanFeature):
  """Feature is True if the member is in a party that proposed the bill."""
  def __init__(self):
    Feature.__init__(self, "Member in bill proposing party")

  def Extract(self, member, bill):
    return (member.party in bill.ProposingParties())

# Feature 4: Member<>Bill
class MemberInBillSupportingPartyFeature(BooleanFeature):
  """Feature is True if the member is in a party that supported the bill."""
  def __init__(self):
    Feature.__init__(self, "Member in bill supporting party")

  def Extract(self, member, bill):
    return (member.party in bill.JoiningParties())

# Feature 5: Member
class MemberInCoalitionFeature(BooleanFeature):
  """Feature is True if the member is in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Member in coalition")

  def Extract(self, member, bill):
    return member.party.is_in_coalition

# Feature 7
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
  return [MemberProposedBillFeature(), # Feature 1
          MemberSupportedBillFeature(), # Feature 2
          MemberInBillProposingPartyFeature(), # Feature 3
          MemberInBillSupportingPartyFeature(), # Feature 4
          MemberInCoalitionFeature(), # Feature 5
          BillProposingPartyInCoalitionFeature(), # Feature 1 @feature.py
          BillSupportingPartyInCoalitionFeature(), # Feature 2 @feature.py
          BillProposingPartyInOppositionFeature(), # Feature 3 @feature.py
          BillSupportingPartyInOppositionFeature(), # Feature 4 @feature.py
          BillSupportingAgendaFeature(), # Feature 5 @feature.py
          BillHasTagFeature(), # Feature 6 @feature.py
          # BillHasKeyWords(bag_of_words), # Feature 6
         ]

class MemberBillsFeatureExtractor:
  def Extract(self, member, bills, features):
    feature_values = {}
    for bill in bills:
      values = []
      for feature in features:
        if isinstance(feature, FeatureSet):
          values.extend(feature.Extract(member, bill))
        else:
          values.append(feature.Extract(member, bill))
      classification = MemberBillFeaturesUtils.ExtractClassification(member, bill)
      bill_date = max([vote.time for vote in bill.vote_set.all()])
      feature_values[bill.id] = tuple((tuple(values), classification, bill_date))

    return feature_values
