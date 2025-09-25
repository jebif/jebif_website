from django.contrib import admin
from django.contrib import messages
#from django.utils.timezone import now  # Unused for now, but could be changed

import jebif_election.models as election
import jebif_users.models as jebif_users



class CandidateInline(admin.TabularInline):
    model = election.Candidates

class VoteInline(admin.TabularInline):  
    model = election.Vote
    readonly_fields = ('date', 'candidat', 'voter', 'has_voted', 'choix')
    fields = ('date', 'candidat', 'has_voted', 'choix')

class ElectionAdmin( admin.ModelAdmin ) :
    inlines = [CandidateInline, VoteInline]
    list_display = ('label', 'waiting', 'opened', 'ended')
    actions = ['populate_voters', 'check_integrity', 'open', 'close', 'end']

    @admin.action(description="New Check integrity of selected elections")
    def check_integrity(self, request, queryset):
        for el in queryset:  
            for candidat in el.candidats.all():
                flat_voter_ids = list(candidat.vote.values_list("voter", flat=True))
                all_voter_ids = list(candidat.vote.values_list("voter"))
                #check number of votes
                if len(flat_voter_ids) != len(set(all_voter_ids)):                   
                    messages.error(request, f"{el.label}: duplicated voters for candidat {candidat.label}!!")
                else:
                    messages.success(request, f"{el.label}: No integrity issue with the number of voters for candidat {candidat.label}.")

    def _set_opened( self, request, queryset, opened ) :
        queryset.update(opened=opened)
        queryset.update(waiting=False)

    @admin.action(description="Open selected elections")
    def open( self, request, queryset ) :
        return self._set_opened(request, queryset, True)

    @admin.action(description="Close selected elections")
    def close( self, request, queryset ) :
        return self._set_opened(request, queryset, False)
    
    @admin.action(description="End selected elections")
    def end(self, request, queryset) :
        for el in queryset:
            el.ended=True
            el.waiting=False
            el.opened=False
            #el.end_date=now #for now unused, but could be if methods to check open/close are changed
            el.save()
            
		
    @admin.action(description="Populate voters of selected elections")
    def populate_voters( self, request, queryset ) :
        for el in queryset :
            for candidat in el.candidats.all():
                new_voters = jebif_users.UserInfo.objects.filter(is_member=True, is_deleted=False).exclude(vote__election=el, vote__candidat=candidat, vote__has_voted=True)
                #Create a line for the vote of each user for each candidat in the election      #WARNING: creates a lot of lines at once
                for userinfo in new_voters :
                    election.Vote.objects.create(
                        election=el,
                        candidat=candidat,
                        voter=userinfo,
                    )
                messages.success(request, f"{el}: {new_voters.count()} voter(s) added for the election of candidate {candidat}")



class PendingCandidateAdmin(admin.ModelAdmin):
    model=election.PendingCandidates
    list_display = ('user', 'label', 'pending',)
    actions = ['validate_candidature', 'unvalidate_candidature',]

    @admin.action(description="Validate candidatures")
    def validate_candidature(self, request, queryset):
        count = 0
        for pending in queryset:
            if pending.pending==True:
                election.Candidates.objects.create(election=pending.election,
                                                label=pending.label,
                                                description=pending.description)
                pending.pending=False
                pending.save()
                count += 1
            else:
                messages.error(request, f"{pending.label} was removed from the pending candidatures, it can't be validated.")
        messages.success(request, f"{count} Candidate(s) added for next election(s)")

    @admin.action(description="Unvalidate candidatures")
    def unvalidate_candidature(self, request, queryset):
        count = 0
        for pending in queryset:
            if pending.pending==True:
                pending.pending=False
                pending.save()
                count += 1
            else:
                messages.error(request, f"{pending.label} was already removed from the pending candidatures, it can't be unvalidated again.")
        messages.success(request, f"{count} Candidate(s) was(were) marked as not pending.")



admin.site.register(election.Election, ElectionAdmin)   

admin.site.register(election.PendingCandidates,PendingCandidateAdmin)
