import json
import re
import time
import traceback
import urllib

from forecast.models import *

def OldOknessetURL(entity):
  return 'http://oknesset.org/api/%s?format=json' % entity

def OknessetURL(entity):
  return 'http://oknesset.org/api/v2/%s?format=json' % entity

def MemberURL(member_id=''):
  return OknessetURL('member/%s' % member_id)

def PartyURL(party_id=''):
  return OknessetURL('party/%s' % party_id)

def AgendaURL(agenda_id=''):
  return OknessetURL('agenda/%s' % agenda_id)

def BillURL(bill_id='', offset=0, old=False):
  if bill_id:
    if old:
      return OldOknessetURL('bill/%s' % bill_id)
    else:
      return OknessetURL('bill/%s' % bill_id)
  else:
    return OknessetURL('bill/') + ('&offset=%d&limit=50' % offset)

def VoteURL(vote_id='', old=False):
  if old:
    return OldOknessetURL('vote/%s' % vote_id)
  else:
    return OknessetURL('vote/%s' % vote_id)

TEXT_SCORE_TO_SCORE = {
    u'\u05ea\u05de\u05d9\u05db\u05d4 \u05de\u05dc\u05d0\u05d4': 1.0,
    u'\u05ea\u05de\u05d9\u05db\u05d4 \u05d7\u05dc\u05e7\u05d9\u05ea': 0.5,
    u'\u05dc\u05d0 \u05e0\u05d9\u05ea\u05df \u05dc\u05e7\u05d1\u05d5\u05e2': 0.0,
    u'\u05d4\u05ea\u05e0\u05d2\u05d3\u05d5\u05ea \u05d7\u05dc\u05e7\u05d9\u05ea': -0.5,
    u'\u05d4\u05ea\u05e0\u05d2\u05d3\u05d5\u05ea \u05de\u05dc\u05d0\u05d4': -1.0
}

class DataPopulator:
  """
  This is the main class that populates the data into the DB.

  It scrapes the OpenKnesset website to get the data on all members.
  """
  def __init__(self):
    self.members = {}
    self.committees = {}
    self.parties = {}
    self.tags = {}
    self.agendas = {}
    self.bills = {}
    self.votes = {}

  def PopulateAllData(self):
    self.PopulateAllParties()
    self.PopulateAllMembers()
    self.PopulateAllAgendas()
    self.PopulateAllBills()

  def PopulateAllMembers(self):
    print '='*80
    self.members = {member.id: member for member in Member.objects.all()}
    print 'Fetching members...'
    data = self._GetJSONData(MemberURL())

    if data['meta']['next']:
      raise Exception('Next is not expected in members: %s' % data['meta']['next'])

    total = data['meta']['total_count']
    for i, data_item in enumerate(data['objects']):
      try:
        print 'Progress: (%d/%d)' % (i+1, total)
        member = self._PopulateMemberById(data_item['id'])
        print '='*40
      except Exception, e:
        print e
        traceback.print_exc()
        raise e
    print 'Done.'

  def PopulateAllParties(self):
    print '='*80
    self.parties = {party.id: party for party in Party.objects.all()}
    print 'Fetching parties...'
    data = self._GetJSONData(PartyURL())

    if data['meta']['next']:
      raise Exception('Next is not expected in parties: %s' % data['meta']['next'])

    total = data['meta']['total_count']
    for i, data_item in enumerate(data['objects']):
      try:
        print 'Progress: (%d/%d)' % (i+1, total)
        party = self._PopulateParty(data_item)
        print '='*40
      except Exception, e:
        print e
        traceback.print_exc()
        raise e
    print 'Done.'

  def PopulateAllAgendas(self):
    print '='*80
    self.agendas = {agenda.id: agenda for agenda in Agenda.objects.all()}
    print 'Fetching all agendas...'
    try:
      data = self._GetJSONData(AgendaURL())
      
      if data['meta']['next']:
        raise Exception('Next is not expected in agendas: %s' % data['meta']['next'])

      total = data['meta']['total_count']
      for i, data_item in enumerate(data['objects']):
        print 'Progress: (%d/%d)' % (i+1, total)
        self._PopulateAgendaById(data_item['id'])
        print '='*40
    except Exception, e:
      print e
      traceback.print_exc()

  def PopulateAllBills(self):
    print '='*80
    self.bills = {bill.id: bill for bill in Bill.objects.all()}
    self.tags = {tag.id: tag for tag in Tag.objects.all()}
    print 'Fetching all bills...'
    try:
      data = self._GetJSONData(BillURL())

      page = 0
      total = data['meta']['total_count']
      while True:
        for i, data_item in enumerate(data['objects']):
          print 'Progress: (%d/%d)' % (50*page+i+1, total)
          bill = self._PopulateBill(data_item)
          print '='*40

        if data['meta']['next']:
          offset = data['meta']['offset'] + data['meta']['limit']
          cm = urllib.urlopen(BillURL(offset=offset))
          data = json.load(cm)
          page += 1
        else:
          break
    except Exception, e:
      print "Error at page %d data item %d:" % (page, i)
      print e
      print "Data: '%s'" % data
      traceback.print_exc()
      raise e

  def _GetJSONData(self, url, max_tries=5, wait_between_retries=5):
    tries = 0
    exc = None
    while tries <= max_tries:
      try:
        cm = urllib.urlopen(url)
        data = json.load(cm)
        return data
      except IOError, e:
        exc = e
      except ValueError, e:
        exc = e

      time.sleep(wait_between_retries)
      tries += 1
      print "Retrying... (%d/%d)" % (tries, max_tries)
    else:
      print "--> URL = '%s'" % url
      if exc:
        print "IO ERROR:"
        print exc

    raise IOError("Too many IOErrors, aborting")

  def _PopulateMemberById(self, member_id):
    member_id = int(member_id)
    if member_id in self.members:
      return self.members[member_id]

    try:
      data = self._GetJSONData(MemberURL(member_id))
    except IOError, e:
      print 'Failed getting member %d' % member_id
      raise e

    print 'Parsing data on member %d' % member_id
    party_id = int(data['party_url'].split('/')[2])
    if party_id not in self.parties:
      member = None
    else:
      role = data['current_role_descriptions']
      role = role if role else ''
      member = Member.objects.create(
          id=data['id'],
          name=data['name'],
          role=role,
          img_url=data['img_url'],
          is_current=data['is_current'],
          party=self.parties[party_id]
      )
      member.save()
    self.members[member_id] = member
    #print unicode(member)

#    for _, committee_url in data_item['committees']:
#      if committee_url not in self.committees:
#        self._PopulateCommittee(committee_url)
#      membership = CommitteeMember.objects.create(
#          member=member,
#          committee=self.committees[committee_url]
#      )
#      membership.save()

    return member

  def _PopulateCommittee(self, committee_url):
    if committee_url in self.committees:
      return self.committees[committee_url]

    data = self._GetJSONData(CommitteeURL(committee_url.split('/')[2]))

    print 'Parsing data on%s' % committee_url.replace('/', ' ')
    committee = Committee.objects.create(
        id=data['id'],
        name=data['name'],
    )
    committee.save()
    self.committees[committee_url] = committee
    #print unicode(committee)

    return committee

  def _PopulateParty(self, data_item):
    party_id = int(data_item['id'])
    if party_id in self.parties:
      return self.parties[party_id]

    print 'Parsing data on party %d' % party_id
    party = Party.objects.create(
        id=party_id,
        name=data_item['name'],
        is_in_coalition=data_item['is_coalition'],
        number_of_seats=data_item['number_of_seats'],
    )
    party.save()
    self.parties[party.id] = party
    #print unicode(party)

    return party

  def _PopulateBill(self, data_item):
    bill_id = int(data_item['absolute_url'].split('/')[2])
    if bill_id in self.bills:
      return self.bills[bill_id]

    print 'Parsing data on bill %d' % bill_id
    bill = Bill.objects.create(
        id=bill_id,
        title=data_item['title'],
        full_title=data_item['title'],
        stage=data_item['stage'],
    )
    bill.save()
    self.bills[bill.id] = bill
    #print unicode(bill)

    data_item = self._GetJSONData(BillURL(bill_id))
    if data_item['approval_vote']:
      vote_id = int(data_item['approval_vote'].split('/')[-2])
      vote = self._PopulateVote(vote_id, 'approval', bill)

    for vote_url in data_item['pre_votes']:
      vote_id = int(vote_url.split('/')[-2])
      self._PopulateVote(vote_id, 'pre', bill)

    # TODO(lagi): move tags to API V2
    data_item = self._GetJSONData(BillURL(bill_id, old=True))
    for tag_data in data_item['tags']:
      tag_id = tag_data['id']
      self._PopulateTag(tag_data)
      bill_tag = BillTag.objects.create(
          bill=bill,
          tag=self.tags[tag_id],
      )
      bill_tag.save()

    # TODO(lagi): move proposing mks to API V2
    for member_data in data_item['proposing_mks']:
      member_id = member_data['id']
      member = self._PopulateMemberById(member_id)
      if not member:
        continue
      bill_proposing_member = BillProposingMember.objects.create(
          bill=bill,
          member=member,
      )
      bill_proposing_member.save()

    # TODO(lagi): move joining mks to API V2
    for member_data in data_item['joining_mks']:
      member_id = member_data['id']
      member = self._PopulateMemberById(member_id)
      if not member:
        continue
      bill_joining_member = BillJoiningMember.objects.create(
          bill=bill,
          member=member,
      )
      bill_joining_member.save()

    return bill

  def _PopulateTag(self, data_item):
    tag_id = int(data_item['id'])
    if tag_id in self.tags:
      return self.tags[tag_id]

    print 'Parsing data on tag %d' % tag_id
    tag = Tag.objects.create(
        id=tag_id,
        name=data_item['name'],
    )
    tag.save()
    self.tags[tag.id] = tag
    #print unicode(tag)

    return tag

  def _PopulateVote(self, vote_id, vote_type, bill):
    vote_id = int(vote_id)
    if vote_id in self.votes:
      return self.votes[vote_id]

    data = self._GetJSONData(VoteURL(vote_id))
    print 'Parsing data on vote %s' % vote_id
    vote = Vote.objects.create(
        id=vote_id,
        title=data['title'],
        full_text=data['full_text'],
        summary=data['summary'],
        bill=bill,
        type=vote_type,
        time=data['time'].replace('T', ' ')
    )
    vote.save()
    self.votes[vote.id] = vote
    #print unicode(vote)

    # TODO(lagi): move for votes to API V2
    data = self._GetJSONData(VoteURL(vote_id, old=True))
    for member_id in data['for_votes']:
      member = self._PopulateMemberById(member_id)
      if not member:
        continue
      vote_member_decision = VoteMemberDecision.objects.create(
          member=member,
          vote=vote,
          decision='FOR',
      )
      vote_member_decision.save()

    # TODO(lagi): move against votes to API V2
    for member_id in data['against_votes']:
      member = self._PopulateMemberById(member_id)
      if not member:
        continue
      vote_member_decision = VoteMemberDecision.objects.create(
          member=member,
          vote=vote,
          decision='AGAINST',
      )
      vote_member_decision.save()

    # TODO(lagi): move abstain votes to API V2
    for member_id in data['abstain_votes']:
      member = self._PopulateMemberById(member_id)
      if not member:
        continue
      vote_member_decision = VoteMemberDecision.objects.create(
          member=member,
          vote=vote,
          decision='ABSTAIN',
      )
      vote_member_decision.save()

    # TODO(lagi): move agenda votes to API V2
    for agenda_data in data['agendas'].values():
      agenda_id = int(agenda_data['id'])
      if agenda_id not in self.agendas:
        print 'WARN: skipping agenda %d' % agenda_data['id']
        continue

      agenda = self.agendas[agenda_id]
      vote_agenda = VoteAgenda.objects.create(
          agenda=agenda,
          vote=vote,
          score=self._GetAgendaSupportScore(agenda_data['text_score']),
          reasoning=agenda_data['reasoning'],
      )
      vote_agenda.save()

    return vote

  def _PopulateAgendaById(self, agenda_id):
    agenda_id = int(agenda_id)
    if agenda_id in self.agendas:
      return self.agendas[agenda_id]

    data = self._GetJSONData(AgendaURL(agenda_id))

    print 'Parsing data on agenda %d' % agenda_id
    image = data['image']
    image = image if image else ''
    agenda = Agenda.objects.create(
        id=agenda_id,
        name=data['name'],
        description=data['description'],
        img_url=image,
        owner=data['public_owner_name'],
    )
    agenda.save()
    self.agendas[agenda.id] = agenda
    #print unicode(agenda)

    for party_item in data['parties']:
      party_id = int(party_item['absolute_url'].split('/')[2])
      party_agenda = PartyAgenda.objects.create(
          agenda=agenda,
          party=self.parties[party_id],
          score=party_item['score'],
          volume=party_item['volume'],
      )
      party_agenda.save()

    for member_item in data['members']:
      member_id = int(member_item['absolute_url'].split('/')[2])
      member_agenda = MemberAgenda.objects.create(
          agenda=agenda,
          member=self.members[member_id],
          score=member_item['score'],
          volume=member_item['volume'],
      )
      member_agenda.save()

    return agenda
  
  def _GetAgendaSupportScore(self, text_score):
    return TEXT_SCORE_TO_SCORE.get(text_score, 0.0)

