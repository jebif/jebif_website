from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User

import jebif_election.models as election
import jebif_users.models as jebif_users



class CandidateInline(admin.TabularInline):
    model = election.Candidates

class VoteInline(admin.TabularInline):  
    model = election.Vote
    readonly_fields = ('date', 'candidat', 'voter', 'has_voted', 'choix')

class ElectionAdmin( admin.ModelAdmin ) :
    inlines = [CandidateInline, VoteInline]
    list_display = ('label', 'opened')
    actions = ['populate_voters', 'check_integrity', 'open', 'close']

    @admin.action(description="Check integrity of selected elections")
    def check_integrity(self, request, queryset):   # Useless now?
        for el in queryset:
            voter_ids = list(el.vote.values_list("voter", flat=True))  #need to check if correct #user_id?
            #check number of votes
            if len(voter_ids) != len(set(voter_ids)):
                messages.error(request, f"{el}: duplicated voters!!")
            #elif el.vote_set.count() != el.voter.filter(has_voted=True).count():   #removed since now voters fused with vote
            #    messages.error(request, f"{el}: mismatch number of votes/voters")
            else:
                messages.success(request, f"{el}: No integrity issue with the number of voters.")

    def _set_opened( self, request, queryset, opened ) :
        queryset.update(opened=opened)

    @admin.action(description="Open selected elections")
    def open( self, request, queryset ) :
        return self._set_opened(request, queryset, True)

    @admin.action(description="Close selected elections")
    def close( self, request, queryset ) :
        return self._set_opened(request, queryset, False)
		
    @admin.action(description="Populate voters of selected elections")
    def populate_voters( self, request, queryset ) :
        for el in queryset :
            for candidat in el.candidats.all():
                new_voters = jebif_users.UserInfo.objects.filter(is_member=True, is_deleted=False).exclude(vote__election=el)
                #Create a line for the vote of each user for each candidat in the election      #WARNING: creates a lot of lines at once
                for mi in new_voters :
                    election.Vote.objects.create(
                        election=el,
                        candidat=candidat,
                        voter=mi,
                    )
                messages.success(request, f"{el}: {new_voters.count()} voter(s) added for the election of candidate {candidat}")



admin.site.register(election.Election, ElectionAdmin)   

