from forecast.models import *
from django.contrib import admin

class CommitteeMemberInline(admin.TabularInline):
  model = CommitteeMember
  extra = 0

class MemberInline(admin.TabularInline):
  model = Member
  extra = 0

class BillTagInline(admin.TabularInline):
  model = BillTag
  extra = 0

class BillProposingMemberInline(admin.TabularInline):
  model = BillProposingMember
  extra = 0

class BillJoiningMemberInline(admin.TabularInline):
  model = BillJoiningMember
  extra = 0

class VoteInline(admin.TabularInline):
  model = Vote
  extra = 0

class VoteAgendaInline(admin.TabularInline):
  model = VoteAgenda
  extra = 0

class VoteMemberDecisionInline(admin.TabularInline):
  model = VoteMemberDecision
  extra = 0

class PartyAgendaInline(admin.TabularInline):
  model = PartyAgenda
  extra = 0

class MemberAgendaInline(admin.TabularInline):
  model = MemberAgenda
  extra = 0

class PartyAdmin(admin.ModelAdmin):
  inlines = [MemberInline]
  list_display = ('name', 'is_in_coalition', 'number_of_seats', 'id')
  list_filter = ['is_in_coalition']
  search_fields = ['name']

class MemberAdmin(admin.ModelAdmin):
  inlines = [
      CommitteeMemberInline,
      BillProposingMemberInline,
      BillJoiningMemberInline,
      VoteMemberDecisionInline
  ]
  list_display = ('name', 'party', 'role', 'img_url', 'is_current', 'id')
  list_filter = ['party', 'is_current']
  search_fields = ['name']

class CommitteeAdmin(admin.ModelAdmin):
  inlines = [CommitteeMemberInline]
  list_display = ('name', 'id')
  list_filter = ['members']
  search_fields = ['name']

class AgendaAdmin(admin.ModelAdmin):
  inlines = [VoteAgendaInline, MemberAgendaInline, PartyAgendaInline]
  list_display = ('name', 'description', 'owner', 'img_url', 'id')
  search_fields = ['name']

class TagAdmin(admin.ModelAdmin):
  inlines = [BillTagInline]
  list_display = ('name', 'id')
  search_fields = ['name']

class BillAdmin(admin.ModelAdmin):
  inlines = [VoteInline, BillTagInline, BillProposingMemberInline, BillJoiningMemberInline]
  list_display = ('title', 'full_title', 'stage', 'id')
  list_filter = ['tags', 'stage']
  search_fields = ['title', 'proposing_members', 'joining_members']

class VoteAdmin(admin.ModelAdmin):
  inlines = [VoteAgendaInline, VoteMemberDecisionInline]
  list_display = ('title', 'full_text', 'summary', 'bill', 'type', 'time', 'id')
  list_filter = ['type', 'time']
  search_fields = ['title']

admin.site.register(Party, PartyAdmin)
admin.site.register(Member, MemberAdmin)
admin.site.register(Committee, CommitteeAdmin)
admin.site.register(Agenda, AgendaAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Bill, BillAdmin)
admin.site.register(Vote, VoteAdmin)
