from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.db.models import Count, Q

import datetime

import jebif_main.settings as settings
import jebif_users.models as jebif_users



class Election( models.Model ) :
    opened = models.BooleanField(default=False)
    label = models.CharField("Libellé", max_length=50)
    max_choices = models.PositiveSmallIntegerField()            #what's the use?
    min_choices = models.PositiveSmallIntegerField(default=0)   #what's the use?
    intro = models.TextField("Introduction")
	#voteA_label = models.CharField("Vote A", max_length=150, blank=True)   #keep it or not?
	#voteB_label = models.CharField("Vote B", max_length=150, blank=True)   #keep it or not?
    date = models.DateTimeField(default=now)
    waiting = models.BooleanField(default=False) #to allow users to candidate for an election
    ended = models.BooleanField(default=False)
	
    def __str__( self ) :
        return f"{self.label}"
	
    def get_absolute_url( self ) :
        return f"/{settings.ROOT_URL}/{self.id}/"
    
    def get_results(self):
        return (
            self.candidats.annotate(
                oui=Count("vote", filter=Q(vote__choix=Vote.Choices.OUI)),
                non=Count("vote", filter=Q(vote__choix=Vote.Choices.NON)),
                abstention=Count("vote", filter=Q(vote__choix=Vote.Choices.ABSTENTION)),
                total=Count("vote"),
            )
        )


class Candidates(models.Model):
	election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidats')
	label = models.CharField("Libellé", max_length=150)
	description = models.TextField("Description")

	def __str__( self ) :
		return f"{self.election.label}/{self.label}"


class Vote(models.Model):
    class Choices(models.TextChoices):
        OUI = "OUI", "Oui"
        NON = "NON", "Non"
        ABSTENTION = "ABST", "S'abstient"
        
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="vote")
    candidat = models.ForeignKey(Candidates, on_delete=models.CASCADE, related_name="vote")
    voter = models.ForeignKey(jebif_users.UserInfo, on_delete=models.CASCADE, related_name="vote")
    choix = models.CharField(max_length=10, choices=Choices.choices, default=Choices.ABSTENTION)
    date = models.DateTimeField(auto_now_add=True)
    has_voted = models.BooleanField(default=False)
    
    def __str__( self ) :
        return f"{self.candidat.election.label}/{self.candidat.label}/{self.voter.user.username}"

    def check_duo_elect_candid(self):
        el_candidat = self.candidat.election.id
        if el_candidat != self.election.id:    #change that with an assert
            print("Error: incorrect duo candidat/election.")


class PendingCandidates(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='pending_candidats')
    label = models.CharField("Libellé", max_length=150)
    description = models.TextField("Description")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='utilisateur')
    pending = models.BooleanField(default=True)

    def __str__( self ) :
        return f"{self.election.label}/{self.label}/{self.user}"
	

def get_election_results(election_id):
    el = Election.objects.get(id=election_id)
    results = (
        el.candidats
        .annotate(
            oui=Count("vote", filter=Q(vote__choix=Vote.Choices.OUI)),
            non=Count("vote", filter=Q(vote__choix=Vote.Choices.NON)),
            abstention=Count("vote", filter=Q(vote__choix=Vote.Choices.ABSTENTION)),
            total=Count("vote"),))

    return results