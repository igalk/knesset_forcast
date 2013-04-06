CACHE = True

MEMBER_DIR = "features/members/"
def MemberPath(member_id):
  return MEMBER_DIR + "member_votes_%s.arff" % member_id

PARTY_DIR = "features/parties/"
def PartyPath(party_id):
  return PARTY_DIR + "party_votes_%s.arff" % party_id
