from django import forms

from jebif_election.models import PendingCandidates

# to add fields for crispy
#from crispy_forms.helper import FormHelper
#from crispy_forms.layout import Layout, Field, Submit

class NewVoteForm(forms.Form):
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

        # Check that user has rights
        if (self.user and not self.user.info.is_member) or (not self.user):
            raise forms.ValidationError("❌ Vous ne pouvez pas remplir ce formulaire.")

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
                                                            #widget=forms.RadioSelect,          # If we want to click one between many
                                                            required=True)

    def clean(self):
        cleaned_data = super().clean()
        election = cleaned_data.get("election")
        # Check if user is a member
        if (self.user and not self.user.info.is_member) or (not self.user):
            raise forms.ValidationError("❌ Vous ne pouvez pas remplir ce formulaire.")
        
        # Check if another candidature from the user already exist
        exists = PendingCandidates.objects.filter(
                user=self.user, election=election
            ).exists()
        if exists:
                raise forms.ValidationError(
                    "❌ Vous avez déjà soumis une candidature pour cette élection."
                )

        return cleaned_data
    

    def save(self, commit = True):
        candidat = super().save(commit=False)
        if self.cleaned_data.get("election"):
            candidat.election = self.cleaned_data["election"]
        if commit:  
            candidat.save()
        return candidat