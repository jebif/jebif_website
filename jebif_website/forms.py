from django import forms

from jebif_website.models import Events, Participant, Article
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

import datetime

class NewEventForm(forms.ModelForm):
    helper = FormHelper()
    helper.add_input(Submit('submit', 'Soumettre', css_class='btn-primary'))
    #Form for users to propose events
    class Meta:
        model = Events
        fields = ["title", "date", "localisation", "description", "max_participants",]

    title = forms.CharField(label="Le nom de votre événement", max_length=50)
    date = forms.DateTimeField(label="Date de l'événement", 
                           initial=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                           widget=forms.DateTimeInput(attrs={"type": "datetime"}),
                           input_formats=["%Y-%m-%d %H:%M"],  # format requested by input[type=date]
                           )
    localisation = forms.CharField(label="Lieu de l'événement")
    description = forms.CharField(label="Description (500 caractères max)", max_length=500)
    max_participants = forms.IntegerField(label="Nombre de participants maximum, '-1' pour aucune limite", max_value=200, min_value=-1)
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # Check if user is a member
        if (self.user and not (self.user.info.is_member or self.user.is_superuser)) or (not self.user):
            raise forms.ValidationError("❌ Vous ne pouvez pas remplir ce formulaire.")

        # If the user is a superuser, validate automatically the event
        if (self.user.is_superuser):
            self.pending=False
            self.active=True
        
        # Check if another pending event from the user already exist
        exists = Events.objects.filter(
                organiser=self.user
            ).filter(pending=True).exists()
        if exists:
                raise forms.ValidationError(
                    "❌ Vous avez déjà un événement en cours de validation."
                )

        return cleaned_data
    

#Class to be able to change the presentation in the Administration
class ArticleAdminForm(forms.ModelForm):
    helper = FormHelper()
    helper.add_input(Submit('register', 'Enregistrer', css_class='btn-primary'))
    class Meta:
        model = Article
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Replace queryset by a custom ModelChoiceField 
        self.fields["subcategory"].label_from_instance = lambda obj: f"{obj.name} ({obj.category.name})"

class ParticipantForm(forms.ModelForm):
    helper = FormHelper()
    helper.add_input(Submit('register', "S'inscrire à l'événement", css_class='btn-primary'))
    class Meta:
        model = Participant
        fields = ("first_name", "last_name", "email", "image_use")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        exists = Participant.objects.filter(event=self.event, email=email).exists()
        if exists:
            raise forms.ValidationError(
                    "❌ Vous vous êtes déjà inscrit à cet événement."
                )
        else:
            if self.user:
                cleaned_data["user"] = self.user
            
        return cleaned_data


class ContactForm(forms.Form):
    helper = FormHelper()
    helper.add_input(Submit('send_mail', 'Envoyer', css_class='btn-primary'))
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