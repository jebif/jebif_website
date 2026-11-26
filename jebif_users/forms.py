from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.forms import ModelForm, Form, EmailField, ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import UserInfo


def email_in_use(email, exclude_user=None):
    """True if `email` (case-insensitive) is already used by another account,
    either in User or in UserInfo (both must stay unique)."""
    users = User.objects.filter(email__iexact=email)
    infos = UserInfo.objects.filter(email__iexact=email)
    if exclude_user is not None:
        users = users.exclude(pk=exclude_user.pk)
        infos = infos.exclude(user=exclude_user)
    return users.exists() or infos.exists()


class UserRegisterForm(UserCreationForm):
    helper = FormHelper()
    helper.form_tag = False     # the template provides the <form> tag
    helper.add_input(Submit('register', 'Enregistrer', css_class='btn-primary'))
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data['email'])
        if email_in_use(email):
            raise forms.ValidationError("Il y a déjà un compte avec cette adresse mail !")
        return email


class UserModificationForm(forms.ModelForm):
# Form to change User fields in the profile
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
        self.fields["email"].required = True

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data.get("email"))
        if email and email_in_use(email, exclude_user=self.instance):
            raise forms.ValidationError("Cette adresse mail est déjà utilisée par un autre compte.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password or confirm_password:
            if not current_password:
                self.add_error("current_password", "Veuillez entrer votre mot de passe actuel.")
            elif not self.user.check_password(current_password):
                self.add_error("current_password", "Le mot de passe actuel est incorrect.")
            elif new_password != confirm_password:
                self.add_error("confirm_password", "Les nouveaux mots de passe ne correspondent pas.")
            else:
                # Same rules as at registration (AUTH_PASSWORD_VALIDATORS)
                try:
                    validate_password(new_password, self.user)
                except ValidationError as e:
                    self.add_error("new_password", e)
        return cleaned_data

    def email_changed(self):
        return "email" in self.changed_data

    def password_changed(self):
        return bool(self.cleaned_data.get("new_password"))

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
    helper.form_tag = False     # the template provides the <form> tag
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
            info = UserInfo.objects.get(email__iexact=data)
        except UserInfo.DoesNotExist :
            raise ValidationError(u"E-mail inconnu")
        return info
