from django import forms
from django.utils import timezone

from jebif_website.models import Events, Participant, Article
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class HoneypotMixin(forms.Form):
    # Anti-bot field: hidden to humans, bots tend to fill every field.
    website_pot = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_website_pot(self):
        # Honeypot: the method name MUST match the field name (website_pot),
        # otherwise it is never called and bots are not detected.
        data = self.cleaned_data.get('website_pot')
        if data:
            raise forms.ValidationError("Spam détecté.")
        return data


def _now_local():
    # Callable: evaluated each time the form is displayed (not once at server start)
    return timezone.localtime().replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")


class NewEventForm(forms.ModelForm):
    helper = FormHelper()
    helper.form_tag = False     # the template provides the <form> tag
    helper.add_input(Submit('submit', 'Soumettre', css_class='btn-primary'))
    #Form for users to propose events
    class Meta:
        model = Events
        fields = ["title", "date", "localisation", "description", "max_participants",]

    title = forms.CharField(label="Le nom de votre événement", max_length=100)
    date = forms.DateTimeField(label="Date de l'événement (heure de Paris)",
                           initial=_now_local,
                           widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
                           input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],  # format sent by input[type=datetime-local]
                           )
    localisation = forms.CharField(label="Lieu de l'événement", max_length=100)
    description = forms.CharField(label="Description (500 caractères max)", max_length=500, widget=forms.Textarea)
    max_participants = forms.IntegerField(label="Nombre de participants maximum, '-1' pour aucune limite", max_value=200, min_value=-1, initial=-1)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date < timezone.now():
            raise forms.ValidationError("La date de l'événement est déjà passée.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        # Check if user is a member (with a membership that has not expired)
        user_info = getattr(self.user, "info", None) if self.user else None
        is_member = bool(user_info and user_info.is_active_member)
        if (not self.user) or (not (is_member or self.user.is_superuser)):
            raise forms.ValidationError("❌ Vous ne pouvez pas remplir ce formulaire.")

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
    class Meta:
        model = Article
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Show the category next to the subcategory name in the choice list
        self.fields["subcategory"].label_from_instance = lambda obj: f"{obj.name} ({obj.category.name if obj.category else '-'})"


class ParticipantForm(HoneypotMixin, forms.ModelForm):
    helper = FormHelper()
    helper.form_tag = False     # the template provides the <form> tag
    helper.add_input(Submit('register', "S'inscrire à l'événement", css_class='btn-primary'))
    class Meta:
        model = Participant
        fields = ("first_name", "last_name", "email", "know_from", "k_f_text", "image_use")

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if email and Participant.objects.filter(event=self.event, email__iexact=email).exists():
            raise forms.ValidationError(
                    "❌ Vous vous êtes déjà inscrit à cet événement."
                )
        return cleaned_data


class ContactForm(HoneypotMixin, forms.Form):
    helper = FormHelper()
    helper.form_tag = False     # the template provides the <form> tag
    helper.add_input(Submit('send_mail', 'Envoyer', css_class='btn-primary'))
    name = forms.CharField(label="Nom", max_length=50)
    email = forms.EmailField(label="Adresse mail de contact")
    commentary = forms.CharField(widget=forms.Textarea, label="Commentaire", max_length=5000)

    def clean_name(self):
        # The name goes in the e-mail subject: a line break would make sending fail
        name = self.cleaned_data["name"]
        if "\n" in name or "\r" in name:
            raise forms.ValidationError("Le nom ne peut pas contenir de retour à la ligne.")
        return name
