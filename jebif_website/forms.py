from django import forms

from jebif_website.models import PendingEvents, Article

import datetime

class NewEventForm(forms.ModelForm):
    #Form for users to propose events
    class Meta:
        model = PendingEvents
        fields = ["title", "date", "localisation", "description",]

    title = forms.CharField(label="Le nom de votre évènement", max_length=50)
    date = forms.DateField(label="Date de l'évènement", 
                           initial=datetime.date.today,
                           widget=forms.DateInput(attrs={"type": "date"}),
                           input_formats=["%Y-%m-%d"],  # format requested by input[type=date]
                           )
    localisation = forms.CharField(label="Lieu de l'évènement")
    description = forms.CharField(label="Description (500 caractères max)", max_length=500)
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # Check if user is a member
        if (self.user and not self.user.info.is_member) or (not self.user):
            raise forms.ValidationError("❌ Vous ne pouvez pas remplir ce formulaire.")
        
        # Check if another pending event from the user already exist
        exists = PendingEvents.objects.filter(
                user=self.user
            ).exists()
        if exists:
                raise forms.ValidationError(
                    "❌ Vous avez déjà proposé un évènement."
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
