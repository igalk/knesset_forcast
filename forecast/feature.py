from models import *

class Feature:
  def __init__(self, name):
    self.name = name

  def LegalValues(self):
    raise Exception('Not implemented')

  def Extract(self, member, bill):
    raise Exception("Not implemented")

  def class_name(self):
    return self.name.replace("'", "").replace(' ', '_').lower()

class BooleanFeature(Feature):
  def LegalValues(self):
    return tuple((True, False))

class FeatureSet(Feature):
  def __init__(self, name, features):
    Feature.__init__(self, name)
    self.features = features

  def LegalValues(self):
    return list([feature.LegalValues() for feature in self.features])

  def Extract(self, member, bill):
    return list([feature.Extract(member, bill) for feature in self.features])

  def class_name(self):
    return list([feature.class_name() for feature in self.features])

DECISION_OPTIONS = ['FOR', 'AGAINST', 'ABSTAIN', 'NO_SHOW']

class MajorityDecision:
  def __init__(self):
    self.decisions = {option: 0 for option in DECISION_OPTIONS}

  def AddDecision(self, decision):
    assert decision in DECISION_OPTIONS
    self.decisions[decision] += 1

  def GetDecision(self):
    if self.decisions['FOR'] > self.decisions['AGAINST']:
      # More for than against
      return 'FOR'
    if self.decisions['FOR'] < self.decisions['AGAINST']:
      # More against than for
      return 'AGAINST'
    if self.decisions['ABSTAIN'] > 0 or self.decisions['FOR'] > 0:
      # for==against > 0
      return 'ABSTAIN'
    return 'NO_SHOW'

# Feature 1: Bill
class BillProposingPartyInCoalitionFeature(BooleanFeature):
  """Feature is True if the bill was proposed by a party in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Bill proposed by a party in the coalition")

  def Extract(self, no_one, bill):
    return any([proposing_party.is_in_coalition
                for proposing_party in bill.ProposingParties()])

# Feature 2: Bill
class BillSupportingPartyInCoalitionFeature(BooleanFeature):
  """Feature is True if the bill was supported by a party in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Bill supported by party in the coalition")

  def Extract(self, no_one, bill):
    return (any([joining_party.is_in_coalition
                for joining_party in bill.JoiningParties()]) or
            any([proposing_party.is_in_coalition
                for proposing_party in bill.ProposingParties()]))

# Feature 3: Bill
class BillProposingPartyInOppositionFeature(BooleanFeature):
  """Feature is True if the bill was proposed by a party in the oposition."""
  def __init__(self):
    Feature.__init__(self, "Bill proposed by party in the oposition")

  def Extract(self, no_one, bill):
    return any([(not proposing_party.is_in_coalition)
                for proposing_party in bill.ProposingParties()])

# Feature 4: Bill
class BillSupportingPartyInOppositionFeature(BooleanFeature):
  """Feature is True if the bill was supported by a party in the oposition."""
  def __init__(self):
    Feature.__init__(self, "Bill supported by party in the oposition")

  def Extract(self, no_one, bill):
    return (any([(not joining_party.is_in_coalition)
                for joining_party in bill.JoiningParties()]) or
            any([(not proposing_party.is_in_coalition)
                for proposing_party in bill.ProposingParties()]))

# Feature 5: Bill
class BillSupportingAgendaFeature(FeatureSet):
  """Feature is a score of how supporting the bill is for an agenda"""

  class ScoredBillSupportingAgendaFeature(Feature):
    def __init__(self, agenda):
      Feature.__init__(self, "Bill supporting agenda %s" % str(agenda.id))
      self.agenda = agenda
      self.agenda_votes = set(agenda.votes.all())

    def Extract(self, member, bill):
      related = set(bill.vote_set.all()).intersection(self.agenda_votes)

      num_bill_agendas = sum([len(VoteAgenda.objects.filter(vote_id__exact=vote.id))
                              for vote in bill.vote_set.all()])
      if num_bill_agendas == 0:
        return '?'

      vote_agendas = [VoteAgenda.objects.filter(agenda_id__exact=self.agenda.id, vote_id__exact=vote.id)[0]
                      for vote in related]

      #if not vote_agendas:
      #  return '?'

      score = sum([v.score for v in vote_agendas])
      if score:
        score /= abs(score)

      return str(int(score))

    def LegalValues(self):
      return ['-1', '0', '1']

  def __init__(self):
    features = [self.ScoredBillSupportingAgendaFeature(agenda) for agenda in Agenda.objects.all()]
    FeatureSet.__init__(self, "Bill supporting agenda", features)

# Feature 6: Bill
class BillHasTagFeature(FeatureSet):
  """Feature is a boolean value indicating that the bill has this tag"""

  class BillHasSingleTagFeature(Feature):
    def __init__(self, tag):
      Feature.__init__(self, "Bill has tag %s" % str(tag.id))
      self.tag = tag

    def Extract(self, member, bill):
      bill_tag = BillTag.objects.filter(tag_id__exact=self.tag.id, bill_id__exact=bill.id)
      if bill_tag:
        return '1'
      return '0'

    def LegalValues(self):
      return ['0', '1']

  def __init__(self):
    features = [self.BillHasSingleTagFeature(tag) for tag in Tag.objects.all()]
    FeatureSet.__init__(self, "Bill has tag", features)
