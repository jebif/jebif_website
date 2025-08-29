from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm, Form, EmailField, ValidationError

from .models import MembershipInfo

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


# Potential conflict here
class MembershipInfoForm( ModelForm ) :
	class Meta :
		model = MembershipInfo
		fields = ("firstname", "lastname", "email", 
						"laboratory_name", "laboratory_cp",
						"laboratory_city", "laboratory_country",
						"position", "motivation")
		
class MembershipInfoEmailForm( Form ) :
	email = EmailField(required=True)

	def clean_email( self ) :
		data = self.cleaned_data["email"]
		try :
			info = MembershipInfo.objects.get(email=data)
		except MembershipInfo.DoesNotExist :
			raise ValidationError(u"E-mail inconnu")
		return info
