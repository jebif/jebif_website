from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.db.models import Count, Q

import datetime

import jebif_users.models as jebif_users

def default_end():
    '''
	Obtain a default date for the end of the elections, one day later.

	Parameters
	----------

	Returns
	-------
		A default date, tomorrow.

	'''
    return now() + datetime.timedelta(days=1)


class Election( models.Model ) :
    '''
	Object representing an Election.
	...

	Attributes
	----------
    opened : bool (Default=False)
        Is the election open so the users can vote

    label : str
        Name of the Election

    intro : str
        Description of the Election

    start_date : date object
        Starting date of the Election

    end_date : date object
        Ending date of the Election

    waiting : bool
        Is the election not open yet, so people can candidate

    ended : bool
        Is the election done, so people can see the results

    Methods
	-------
    get_results()
        For each candidat of the election, annotate 4 values: number of "oui" votes,
        number of "no" votes, number of "abstention" and the total number of votes for this candidate.
    '''
    opened = models.BooleanField(default=False)
    label = models.CharField("Libellé", max_length=50)
    intro = models.TextField("Introduction")
    start_date = models.DateTimeField(default=now)
    end_date = models.DateTimeField(default=default_end)
    waiting = models.BooleanField(default=False) #to allow users to candidate for an election
    ended = models.BooleanField(default=False)  #to close an election, so the results can be seen
	
    def __str__( self ) :
        return f"{self.label}"
    
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
    '''
	Object representing a Candidat for an Election. It can also be used for a "Vote",
    like for "Bilan moral", etc.
	...

	Attributes
	----------
    election : str
        Name (label) of the election in which was this Candidate

    label : str
        Name of the Candidat (or "Vote")

    description : str
        Description of the Candidat (or "Vote")

    pdffile : str
        PDF file related to the Candidat (or "Vote"). Only accesible during creation to the admin.

    Methods
	-------
    '''
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidats')
    label = models.CharField("Libellé", max_length=150)
    description = models.TextField("Description")
    pdffile = models.FileField(
        upload_to="elections_pdfs/",
        blank=True,
        null=True,
        verbose_name="Document PDF"
    )

    def __str__( self ) :
        return f"{self.election.label}/{self.label}"


class Vote(models.Model):
    '''
	Object representing a choice from a User for a Candidat in an Election.
	...

	Attributes
	----------
    election : str
        Name (label) of the Election for which was this Vote.

    candidat : str
        Name (label) of the Candidat for which was this Vote.

    vote : str
        Name of the User who voted (isn't visible in admin interface, nor anywhere else)

    choix : str (Choice object)
        Choice of the User for this Candidat (basically yes, no, or don't say)

    date : date object
        When the choice was done.

    has_voted : bool
        Check if the user as voted, since the Vote can be created in advance to check if there is still missing votes later
        (but the name of the late voters won't be visible).

    Methods
	-------
    check_duo_elect_candid()
        Check if the candidat is in the correct election.
        Not used yet, shouldn't be needed.
    '''
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
        #Function Not used yet
        el_candidat = self.candidat.election.id
        if el_candidat != self.election.id:    #change that with an assert
            print("Error: incorrect duo candidat/election.")


class PendingCandidates(models.Model):
    '''
	Object representing a future Candidat for an Election. 
    If approved by an Admin, a Candidat should be created for the Election.
    (But this PendingCandidates shouldn't be deleted, 
    to avoid multiple candidatures)
	...

	Attributes
	----------
    election : str
        Name (label) of the election in which was this Candidate

    label : str
        Name of the Candidat (or "Vote")

    description : str
        Description of the Candidat (or "Vote")

    user : str
        User who proposed the candidature.

    pending : bool
        Has this candidature been seen.
        Pending: has not been judged yet (can be validated to create a Candidate, or unvalidated)

    Methods
	-------
    '''
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='pending_candidats')
    label = models.CharField("Libellé", max_length=150)
    description = models.TextField("Description")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pending_candidats')
    pending = models.BooleanField(default=True)

    def __str__( self ) :
        return f"{self.election.label}/{self.label}/{self.user}"
	

def get_election_results(election_id):
    '''
	Obtain the results for an election.

	Parameters
	----------
    election_id : int
        Id of an Election


	Returns
	-------
		The results for each candidat in this Election.

	'''
    el = Election.objects.get(id=election_id)
    results = (
        el.candidats
        .annotate(
            oui=Count("vote", filter=Q(vote__choix=Vote.Choices.OUI)),
            non=Count("vote", filter=Q(vote__choix=Vote.Choices.NON)),
            abstention=Count("vote", filter=Q(vote__choix=Vote.Choices.ABSTENTION)),
            total=Count("vote"),))

    return results