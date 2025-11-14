from django.views import View

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LogoutView, LoginView
from django.contrib.auth.decorators import login_required, user_passes_test

from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from django.conf import settings
from django.core.mail import send_mail
from django.db.transaction import atomic
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse, HttpResponseRedirect

import csv
import datetime
import json
from pathlib import Path

from .models import *
from .forms import *

# Get emails from "Staff" users.
User = get_user_model()
staff_users = User.objects.filter(is_staff=True)
emails = [user.email for user in staff_users if user.email]

fixtures_file = Path(__file__).parent.joinpath("fixtures.json")
with open(fixtures_file,"r") as f:
	old_accounts = json.load(f)

def ask_membership():
    # Function to automatically send a mail to check the membership (new and renew)
	msg_subj = "Demande d'adhésion"
	admin_url = f"http://jebif.fr/admin/auth/user/" 

	msg_txt = f"""Bonjour,
			Une demande d'adhésion ou de ré-adhésion vient d'être postée sur le site. Pour l'accepter' :
			{admin_url}"""
			
	send_mail(
        subject=settings.EMAIL_SUBJECT_PREFIX + msg_subj,
        message=msg_txt,
        from_email=settings.SERVER_EMAIL,
		recipient_list=["iscb.rsg.france@gmail.com"],
        fail_silently=True
        )

def validate_membership( user ):
	# Funtion to automatically send a mail when a membership is validated
	username = user.username
	msg_to = [user.email]
	msg_from = "admin@jebif.rumengol.net"
	msg_subj = f"Ton adhésion à JeBiF"
	msg_txt = f"""
Bonjour {username},

Tu peux modifier ton adhésion à l'association JeBiF en te rendant sur
le site de JeBiF, dans ta page Profile.

À bientôt,
L’équipe JeBiF (RSG-France)
"""
	send_mail(msg_subj, msg_txt, msg_from, msg_to)

	


class RegisterView(View):
	#View to create a new User
	def get(self, request):
		user_form = UserRegisterForm()
		return render(request, 'jebif_users/register.html', {'user_form': user_form})

	def post(self, request):
		
		user_form = UserRegisterForm(request.POST)
		
		if user_form.is_valid():
			with atomic() :
				#creation of User
				user = user_form.save()
				messages.success(request, "✅ Ton compte a été créé, tu as reçu un mail avec un lien pour confirmer ton inscrpition.")
			
			uid = urlsafe_base64_encode(force_bytes(user.pk))
			token = str(user.pk) + "-" + str(datetime.datetime.now().timestamp())

			send_mail(
				subject=f"Creation de compte JeBiF",
				message=f"""
Bonjour {user.username},

Ton compte sur le site de l'association JeBiF vient d'être créé, mais il n'est pas encore actif.
Pour vérifier ton adresse mail, clique sur ce lien (valable 20 minutes): https://jebif.fr/users/verify/{uid}/{token}

Tu pourras ensuite compléter ton profil. Si tu as déjà une adhésion en cours, celle-ci sera conservée.

À bientôt,
L’équipe JeBiF (RSG-France)
""",
				from_email=settings.SERVER_EMAIL,          
				recipient_list=[user.email],
				fail_silently=True
				)
			return redirect('home')
		else:
			messages.error(request, "⚠️ Il y a une ou plusieurs erreur(s) dans le formulaire, merci de les corriger.")
			return render(request, 'jebif_users/register.html', {'user_form': user_form})


def logout(request):
    if request.method == 'POST':
        return LogoutView.as_view(next_page='login')(request)
    else:
        return render(request, 'jebif_users/logout.html')
    

def login(request):
    if request.method == 'POST':
        return LoginView.as_view(next_page='home')(request)
    else:
        return render(request, 'jebif_users/login.html')

class VerifyView(View):
	def get(self, request, uid, token):
		try:
			uid = force_str(urlsafe_base64_decode(uid))
			user = User.objects.get(pk=uid)
		except(TypeError, ValueError, OverflowError, User.DoesNotExist):
			user = None
			uid = 0
		
		token_part = token.split("-")
		valid_uid = token_part[0] == uid
		valid_timestamp = (datetime.datetime.now().timestamp() - float(token_part[1])) <= datetime.timedelta(minutes=20).seconds
		if user is not None and valid_uid and valid_timestamp:
			info_form = UserInfoForm()
			existing_account = False

			for account in old_accounts:
				if account["email"] == user.email:
					inscription = datetime.date.fromisoformat(account["inscription_date"])
					end = inscription.replace(year=2026)

					user_info = UserInfo(
						user=user,
						email=account["email"],
						firstname=account["firstname"],
						lastname=account["lastname"],
						laboratory=account["laboratory_name"],
						city_name=account["laboratory_city"],
						city_cp=account["laboratory_cp"],
						country=account["laboratory_country"],
						position=account["position"],
						motivation=account["motivation"],
						inscription_date=account["inscription_date"],
						is_member=account["active"],
						want_member=False,
						is_deleted=account["deleted"],
						begin_membership=inscription,
						end_membership=end
					)
					if not UserInfo.objects.filter(user=user).exists():
						user_info.save()
						user.info = user_info
						user.save()

					info_form = UserInfoForm(instance=user_info)
					existing_account = True
			return render(request, "jebif_users/fill_info.html", {"existing_account":existing_account, "info_form":info_form})
		else:
			messages.error(request, "⚠️ Bad verification link or it has expired. Please try again.")
			return redirect("home")

	def post(self, request, uid, token):
		uid = force_str(urlsafe_base64_decode(uid))
		user = User.objects.get(pk=uid)
		existing_account = False

		if hasattr(user, "info"):
			user_info = user.info
			info_form = UserInfoForm(request.POST, instance=user_info)
			existing_account = True
		else:
			info_form = UserInfoForm(request.POST)

		if info_form.is_valid():
			with atomic():
				user_info = info_form.save(commit=False)
				if not existing_account:
					user_info.user = user
					user_info.email = user.email
					user_info.want_member = True
				else:
					user_info.want_member = False
				user_info.save()

				user.info = user_info
				user.save()

				if user_info.want_member:
					bonus = "Ton adhésion est en cours d'évaluation par le Conseil d'Administration."
				else:
					bonus = "Ton adhésion a été transférée depuis l'ancien site."
				messages.success(request, f"✅ Tes informations ont été créées. {bonus}")

			auth_login(request, user)
			return redirect("home")
		else:
			messages.error(request, "⚠️ Il y a une ou plusieurs erreur(s) dans le formulaire, merci de les corriger.")
			return render(request, "jebif_users/fill_info.html", {"existing_account":existing_account, "info_form":info_form})


@login_required
def profile_view(request):
	#Function for the profile page, to modify info
	user = request.user

	today = datetime.date.today()

	user_info = request.user.info  # get UserInfo linked to User
	remaining_time = (user_info.end_membership - today).days
	show_button_membership = (user_info.want_member == False) and ((remaining_time <= 30) or (user_info.is_member == False))
	
	if request.method == "POST":
		user_form = UserModificationForm(request.POST, instance=request.user, user=request.user)
		info_form = UserInfoForm(request.POST, instance=user_info)
		if info_form.is_valid() and user_form.is_valid():
			user = user_form.save()
			user_info = info_form.save(commit=False)
			if user.email != user_info.email:
				user_info.email = user.email
			info_form.save()
			return redirect('profile')
	else:
		user_form = UserModificationForm(instance=user)		#retrieve the known info
		info_form = UserInfoForm(instance=user_info)

	return render(request, 'jebif_users/profile.html', {'user_form': user_form, 'info_form': info_form, 'show_button_membership': show_button_membership, 'remaining_time': remaining_time,})

@login_required
def test_mail(request):
	send_mail(
				subject=f"Test Mail",
				message=f"""
Test de mail, envoyé depuis le nouveau site web JeBiF
""",
				from_email=settings.SERVER_EMAIL,          
				recipient_list=["rumengol@proton.me"],
				fail_silently=True
				)
	return redirect('home')

@login_required
def request_membership(request):
	#Function for user to request the membership
	user_info = request.user.info 
	if request.method == "POST":
		user_info.want_member = True
		user_info.save()
		if settings.DEBUG == False:
			ask_membership() #function to send a mail to admin
	return redirect('profile')
      

def is_admin() :
	def validate( u ) :
		return u.is_authenticated and u.is_staff
	return user_passes_test(validate)

@is_admin()
def button_admin(request):
	if request.method == 'POST':
		return redirect('admin_home')
	else:
		return render(request, 'jebif_users/button_admin.html')
	
@is_admin()
def admin_home_view(request):
    return render(request, 'jebif_users/admin_home.html')

@is_admin()
def admin_subscription( request ) :
	infos = UserInfo.objects.filter(is_member=False, is_deleted=False, want_member=True)
	return render(request, "jebif_users/admin_subscription.html", {"infos": infos})


@is_admin()
def admin_subscription_accept( request, info_id ) :
	#Function for the admin page in the website (not the interface) to accept subscription
	with atomic() :
		info = UserInfo.objects.get(id=info_id)
		info.is_member = True
		info.want_member = False
		info.inscription_date = datetime.date.today()
		info.init_date(info.inscription_date)
		info.save()

	msg_from = "admin@jebif.rumengol.net"
	msg_to = [info.email]
	msg_subj = "Bienvenue dans l'association JeBiF"
	msg_txt = f"""
Bonjour {info.firstname},

Nous avons bien pris en compte ton adhésion à l’association JeBiF. N’hésite pas à nous contacter si tu as des questions, des commentaires, des idées, etc…

Tu connais sans doute déjà notre site internet http://jebif.fr. Tu peux aussi faire un tour sur notre page internationale du RSG-France.
http://www.iscbsc.org/rsg/rsg-france

À bientôt,
L’équipe JeBiF (RSG-France)
"""
	send_mail(msg_subj, msg_txt, msg_from, msg_to)

	return HttpResponseRedirect("../../")


@is_admin()
def admin_subscription_reject( request, info_id ) :
	#Function for the admin page in the website (not the interface) to reject subscription
	with atomic() :
		info = get_object_or_404(UserInfo, id=info_id)
		info.is_deleted = True
		info.save()
	return HttpResponseRedirect("../../")


@is_admin()
def admin_export_csv( request ) :
	#Function for the admin page in the website (not the interface) to export the list of members
	charset = 'utf-8'
	response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
	response['Content-Disposition'] = 'attachment; filename=membres_jebif.csv'

	writer = csv.writer(response) # add (,delimiter=';') to change the delimiter
	writer.writerow(['Nom', 'Prénom', 'E-mail',
		'Laboratoire', 'Ville', 'Pays', 'Poste actuel',
		'Motivation', 'Date inscription'])

	infos = UserInfo.objects.filter(is_member=True).extra(select={'ord':'lower(lastname)'}).order_by('ord')

	for i in infos :
		writer.writerow([i.lastname, i.firstname, 
			i.email, i.laboratory, i.city_name,
			i.country, i.position,
			i.motivation.replace("\r\n", " -- "),
			i.inscription_date.isoformat()])

	return response
