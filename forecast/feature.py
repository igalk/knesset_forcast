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

class BillProposingPartyInCoalitionFeature(BooleanFeature):
  """Feature is True if the bill was proposed by a party in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Bill proposed by party in the coalition")

  def Extract(self, no_one, bill):
    return any([proposing_party.is_in_coalition
                for proposing_party in bill.ProposingParties()])

class BillJoiningPartyInCoalitionFeature(BooleanFeature):
  """Feature is True if the bill was joined by a party in the coalition."""
  def __init__(self):
    Feature.__init__(self, "Bill joined by party in the coalition")

  def Extract(self, no_one, bill):
    return any([joining_party.is_in_coalition
                for joining_party in bill.JoiningParties()])

class BillProposingPartyInOpositionFeature(BooleanFeature):
  """Feature is True if the bill was proposed by a party in the oposition."""
  def __init__(self):
    Feature.__init__(self, "Bill proposed by party in the oposition")

  def Extract(self, no_one, bill):
    return any([not proposing_party.is_in_coalition
                for proposing_party in bill.ProposingParties()])

class BillJoiningPartyInOpositionFeature(BooleanFeature):
  """Feature is True if the bill was joined by a party in the oposition."""
  def __init__(self):
    Feature.__init__(self, "Bill joined by party in the oposition")

  def Extract(self, no_one, bill):
    return any([not joining_party.is_in_coalition
                for joining_party in bill.JoiningParties()])
