from django.core.exceptions import ObjectDoesNotExist
from forecast.feature import *
from forecast.member_bills_feature_extractor import MemberBillFeaturesUtils
import itertools

class GenericBillFeaturesUtils:
  @staticmethod
  def ExtractClassification(bill):
    decisions = MajorityDecision()
    for vote in bill.vote_set.all():
      vote_decisions = {v[0]: v[1] for v in [(i[0], len(list(i[1]))) for i in itertools.groupby([d.decision for d in vote.votememberdecision_set.all()])]}
      if vote_decisions.get('FOR', 0) > vote_decisions.get('AGAINST', 0):
        decision = 'FOR'
      elif vote_decisions.get('FOR', 0) < vote_decisions.get('AGAINST', 0):
        decision = 'AGAINST'
      else:
        decision = 'ABSTAIN'

      if vote.type == 'approval':
        return decision
      decisions.AddDecision(decision)
    return decisions.GetDecision()

# Feature 1
class CoalitionProposedBillFeature(BooleanFeature):
  """Feature is True if all proposers of the bill are in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Coalition proposed the Bill")

  def Extract(self, not_used, bill):
    return all([m.party.is_in_coalition for m in bill.proposing_members.all()])

# Feature 2
class OppositionProposedBillFeature(BooleanFeature):
  """Feature is True if all proposers of the bill are in the opposition."""
  def __init__(self):
    Feature.__init__(self, "Opposition proposed the Bill")

  def Extract(self, not_used, bill):
    return all([not m.party.is_in_coalition for m in bill.proposing_members.all()])

# Feature 3
class MostlyCoalitionProposedBillFeature(BooleanFeature):
  """Feature is True if more proposers of the bill are in the coalition than opposition."""
  def __init__(self):
    Feature.__init__(self, "Mostly coalition proposed the Bill")

  def Extract(self, not_used, bill):
    c = [m.party.is_in_coalition for m in bill.proposing_members.all()]
    c.sort()
    counters = {r[0]: r[1] for r in [(i[0], len(list(i[1]))) for i in itertools.groupby(c)]}
    return counters.get(True, 0) > counters.get(False, 0)

# Feature 4
class MostlyCoalitionSupportedBillFeature(BooleanFeature):
  """Feature is True if more supporters of the bill are in the coalition than opposition."""
  def __init__(self):
    Feature.__init__(self, "Mostly coalition supported the Bill")

  def Extract(self, not_used, bill):
    c = [m.party.is_in_coalition for m in bill.proposing_members.all()]
    c.extend([m.party.is_in_coalition for m in bill.joining_members.all()])
    c.sort()
    counters = {r[0]: r[1] for r in [(i[0], len(list(i[1]))) for i in itertools.groupby(c)]}
    return counters.get(True, 0) > counters.get(False, 0)

def GenericBillsFeatures():
  return [CoalitionProposedBillFeature(), # Feature 1
          OppositionProposedBillFeature(), # Feature 2
          MostlyCoalitionProposedBillFeature(), # Feature 3
          MostlyCoalitionSupportedBillFeature(), # Feature 4
          BillProposingPartyInCoalitionFeature(), # Feature 1 @feature.py
          BillSupportingPartyInCoalitionFeature(), # Feature 2 @feature.py
          BillProposingPartyInOppositionFeature(), # Feature 3 @feature.py
          BillSupportingPartyInOppositionFeature(), # Feature 4 @feature.py
          BillSupportingAgendaFeature(), # Feature 5 @feature.py
          BillHasTagFeature(), # Feature 6 @feature.py
         ]

class GenericBillsFeatureExtractor:
  def __init__(self, progress):
    self.progress = progress

  def Extract(self, bills, features):
    feature_values = {}
    for i, bill in enumerate(bills):
      self.progress.WriteProgress("Extract features", i, len(bills))
      print 'Bill (%d/%d)' % (i+1, len(bills))
      values = []
      for feature in features:
        if isinstance(feature, FeatureSet):
          values.extend(feature.Extract(None, bill))
        else:
          values.append(feature.Extract(None, bill))
      classification = GenericBillFeaturesUtils.ExtractClassification(bill)
      bill_date = max([vote.time for vote in bill.vote_set.all()])
      feature_values[bill.id] = tuple((tuple(values), classification, bill_date))

    self.progress.WriteProgress("Extract features", len(bills), len(bills), True)
    return feature_values
