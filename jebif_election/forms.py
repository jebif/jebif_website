from django import forms
from django.core.exceptions import ValidationError

import jebif_election.models as election
from jebif_election.models import Vote, Candidates, PendingCandidates

#from django.utils.translation import gettext_lazy as _ # meh, wth

# to add fields for crispy
#from crispy_forms.helper import FormHelper
#from crispy_forms.layout import Layout, Field, Submit

class VoteForm( forms.Form ) :                      #INCORRECT FOR NOW
    vote = forms.ChoiceField(widget=forms.RadioSelect)
    #candidates = None  # Créé dynamiquement si nécessaire

    def __init__(self, *args, **kwargs):
        election = kwargs.pop('election')
        candidat = kwargs.pop('candidat')
        super().__init__(*args, **kwargs)

        # vote          #ERROR: was made for some stuff like "Bilan", not for elections of one candidat
        self.fields['vote'].label = f"Vote : {election.label} / {candidat.label}"
        self.fields['vote'].choices = Vote._meta.get_field("vote").choices

        """# voteB si applicable
        if election.voteB_label:
            self.fields['voteB'] = forms.ChoiceField(
                label=f"Vote B : {election.voteB_label}",
                choices=Vote._meta.get_field("voteB").choices,
                widget=forms.RadioSelect
            )"""

        # candidats si applicable
        if election.max_choices > 0:
            choices = [(c.id, c.label) for c in election.candidats.all()]

            def validate_candidates(value):
                if len(value) < election.min_choices:
                    raise ValidationError(f"Sélectionnez au moins {election.min_choices} candidat(s).")
                if len(value) > election.max_choices:
                    raise ValidationError(f"Sélectionnez au plus {election.max_choices} candidat(s).")

            self.fields['candidates'] = forms.MultipleChoiceField(
                label=(
                    "Vote C : Renouvellement du Conseil d'Administration - "
                    "\"Voulez-vous que la personne suivante soit élue ?\""
                    + (f" ({election.max_choices} maximum)" if election.max_choices < election.candidats.count()
                       else " (sélectionnez tous les candidats que vous souhaitez voir élus)")
                ),
                required=False,
                choices=choices,
                widget=forms.CheckboxSelectMultiple,
                validators=[validate_candidates]
            )

        """ # passwd : validation spécifique
        def validate_passwd(value):
            if len(value) != 32:
                raise ValidationError("Clef de vote invalide.")
            try:
                v = election.voter.get(passwd=value)
                if v.has_voted:
                    raise ValidationError("Clef de vote déjà utilisée.")
            except Vote.DoesNotExist:
                raise ValidationError("Clef de vote inconnue.")

        self.fields['passwd'].validators.append(validate_passwd)"""



class NewVoteForm(forms.Form):
    #def __init__(self, *args, **kwargs):    
    #    election = kwargs.pop("election")
    #    self.user = kwargs.pop("user", None)
    def __init__(self, *args, userinfo=None, election=None, candidates=None, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        CHOIX = [
            ("OUI", "Oui"),
            ("NON", "Non"),
            ("ABS", "S'abstient"),
        ]

        if candidates is None and election is not None:
            candidates = election.candidats.all()

        for candidat in candidates:
            self.fields[f"candidat_{candidat.id}"] = forms.ChoiceField(
                label=candidat.label,
                choices=CHOIX,
                widget=forms.RadioSelect,  
                required=True
            )
    
    def clean(self):
        cleaned_data = super().clean()

        # Vérifier que l’utilisateur a bien les droits
        if (self.user and not self.user.info.is_member) or (not self.user):
            raise forms.ValidationError("Vous ne pouvez pas remplir ce formulaire.")

        return cleaned_data
    

class NewCandidateForm(forms.ModelForm):
    class Meta:
        model = PendingCandidates
        fields = ["label", "description",]

    label = forms.CharField(label="Votre nom", max_length=50)
    description = forms.CharField(label="Description (500 caractères max)", max_length=500)
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        elections = kwargs.pop("elections", None)
        super().__init__(*args, **kwargs)
        
        if elections is not None:
            self.fields["election"]= forms.ModelChoiceField(queryset=elections,
                                                            label="Candidater pour l'élection:",
                                                            #widget=forms.RadioSelect,
                                                            required=True)

    def clean(self):
        cleaned_data = super().clean()
        election = cleaned_data.get("election")
        # Check if user is a member
        if (self.user and not self.user.info.is_member) or (not self.user):
            raise forms.ValidationError("Vous ne pouvez pas remplir ce formulaire.")
        
        # Check if another candidature from the user already exist
        exists = PendingCandidates.objects.filter(
                user=self.user, election=election
            ).exists()
        if exists:
                raise forms.ValidationError(
                    "Vous avez déjà soumis une candidature pour cette élection."
                )

        return cleaned_data
    

    def save(self, commit = True):
        candidat = super().save(commit=False)
        if self.cleaned_data.get("election"):
            candidat.election = self.cleaned_data["election"]
        if commit:  
            candidat.save()
        return candidat