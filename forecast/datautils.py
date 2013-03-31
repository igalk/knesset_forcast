from django.shortcuts import render_to_response
from forecast.models import *

def erase(request):
  CommitteeMember.objects.all().delete() # Has to be deleted before Member&Committee
  Committee.objects.all().delete() # Has to be deleted before Member
  BillProposingMember.objects.all().delete() # Has to be deleted before Member&Bill
  BillJoiningMember.objects.all().delete() # Has to be deleted before Member&Bill
  VoteMemberDecision.objects.all().delete() # Has to be deleted before Member&Vote
  MemberAgenda.objects.all().delete() # Has to be deleted before Member&Agenda
  PartyAgenda.objects.all().delete() # Has to be deleted before Party&Agenda
  Member.objects.all().delete() # Has to be deleted before Party
  Party.objects.all().delete()
  BillTag.objects.all().delete() # Has to be deleted before Bill&Tag
  Tag.objects.all().delete()
  VoteAgenda.objects.all().delete() # Has to be deleted before Agenda&Vote
  Vote.objects.all().delete() # Has to be deleted before Bill
  Bill.objects.all().delete()
  Agenda.objects.all().delete()

  return render_to_response('db_erased.html')
