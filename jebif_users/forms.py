from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm, Form, EmailField, ValidationError

from .models import UserInfo

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


# Potential conflict here
class UserInfoForm( ModelForm ) :
	class Meta :
		model = UserInfo
		fields = ("firstname", "lastname", 
						"laboratory", "city_cp",
						"city_name", "country",
						"position", "motivation")
		
class UserInfoEmailForm( Form ) :
	email = EmailField(required=True)

	def clean_email( self ) :
		data = self.cleaned_data["email"]
		try :
			info = UserInfo.objects.get(email=data)
		except UserInfo.DoesNotExist :
			raise ValidationError(u"E-mail inconnu")
		return info
