from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm, Form, EmailField, ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import UserInfo

class UserRegisterForm(UserCreationForm):
    helper = FormHelper()
    helper.add_input(Submit('register', 'Enregistrer', css_class='btn-primary'))
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email']).exists():
            raise forms.ValidationError("Il y a déjà un compte avec cette adresse mail !")
        return self.cleaned_data['email']


class UserModificationForm(forms.ModelForm):
# Form to change User fields in the profile
    helper = FormHelper()
    helper.add_input(Submit('register', 'Enregistrer', css_class='btn-primary'))
    current_password = forms.CharField(label="Mot de passe actuel",
                                    widget=forms.PasswordInput,
                                    required=False)
    new_password = forms.CharField(label="Nouveau mot de passe",
                                    widget=forms.PasswordInput,
                                    required=False)
    confirm_password = forms.CharField(label="Confirmer le nouveau mot de passe",
                                    widget=forms.PasswordInput,
                                    required=False)
    class Meta:
        model = User
        fields = ["username", "email", "current_password", "new_password", "confirm_password"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # pour vérifier le mot de passe actuel
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()    #NOT SURE IF SAFE
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password or confirm_password:
            if not current_password:
                raise forms.ValidationError("Veuillez entrer votre mot de passe actuel.")
            if not self.user.check_password(current_password):
                raise forms.ValidationError("Le mot de passe actuel est incorrect.")
            if new_password != confirm_password:
                raise forms.ValidationError("Les nouveaux mots de passe ne correspondent pas.")
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user


class UserInfoForm( ModelForm ) :
    helper = FormHelper()
    helper.add_input(Submit('register', 'Confirmer', css_class='btn-primary'))
    class Meta :
        model = UserInfo
        fields = ("firstname", "lastname", 
                        "laboratory", "city_cp",
                        "city_name", "country",
                        "position", "motivation",
                        "know_from")
        

class UserInfoEmailForm( Form ) :
    helper = FormHelper()
    helper.add_input(Submit('register', 'Enregistrer', css_class='btn-primary'))
    email = EmailField(required=True)

    def clean_email( self ) :
        data = self.cleaned_data["email"]
        try :
            info = UserInfo.objects.get(email=data)
        except UserInfo.DoesNotExist :
            raise ValidationError(u"E-mail inconnu")
        return info
