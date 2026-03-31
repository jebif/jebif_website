from django import forms

from jebif_website.models import Events, Participant, Article

import datetime

class NewEventForm(forms.ModelForm):
    #Form for users to propose events
    class Meta:
        model = Events
        fields = ["title", "date", "localisation", "description",]

    title = forms.CharField(label="Le nom de votre évènement", max_length=50)
    date = forms.DateTimeField(label="Date de l'évènement", 
                           initial=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                           widget=forms.DateTimeInput(attrs={"type": "datetime"}),
                           input_formats=["%Y-%m-%d %H:%M"],  # format requested by input[type=date]
                           )
    localisation = forms.CharField(label="Lieu de l'évènement")
    description = forms.CharField(label="Description (500 caractères max)", max_length=500)
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # Check if user is a member
        if (self.user and not (self.user.info.is_member or self.user.is_superuser)) or (not self.user):
            raise forms.ValidationError("❌ Vous ne pouvez pas remplir ce formulaire.")
        
        # Check if another pending event from the user already exist
        exists = Events.objects.filter(
                organiser=self.user
            ).filter(pending=True).exists()
        if exists:
                raise forms.ValidationError(
                    "❌ Vous avez déjà un évènement en cours de validation."
                )

        return cleaned_data
    

#Class to be able to change the presentation in the Administration
class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Replace queryset by a custom ModelChoiceField 
        self.fields["subcategory"].label_from_instance = lambda obj: f"{obj.name} ({obj.category.name})"

class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.user:
            cleaned_data["user"] = self.user
            
        return cleaned_data


class ContactForm(forms.Form):
    name = forms.CharField(label="Nom", max_length=50)
    email = forms.EmailField(label="Adresse mail de contact")
    commentary = forms.CharField(widget=forms.Textarea, label="Commentaire")

    # Anti-bot field (honeypot)
    website_pot = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_website(self):
        data = self.cleaned_data['website_pot']
        if data:
            raise forms.ValidationError("Spam détecté.")
        return data