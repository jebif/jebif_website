#from django.shortcuts import render, redirect
from django.views import View
#from .forms import UserRegisterForm
from django.contrib.auth.views import LogoutView, LoginView
from django.contrib.auth.decorators import login_required

from django.conf import settings
from django.core.mail import send_mail
from django.db.transaction import atomic

from django.shortcuts import *
#from django.views.generic import TemplateView

from django.contrib.auth.decorators import *
from urllib.parse import quote

from django.urls import reverse

from django.conf import settings


import csv
import datetime

from .models import *
from .forms import *

def ask_membership():
    # Function to automatically send a mail to check the membership (new and renew)
	msg_subj = "Demande d'adhésion"
	#admin_url = f"http://jebif.fr{reverse('admin_subscription')}" #NEED TO CHANGE
	admin_url = f"http://jebif.fr/admin/auth/user/" 

	msg_txt = f"""Bonjour,
			Une demande d'adhésion ou de ré-adhésion vient d'être postée sur le site. Pour l'accepter' :
			{admin_url}"""
	membership_managers = getattr(settings, "MEMBERSHIP_MANAGERS", [])
			
	send_mail(
        settings.EMAIL_SUBJECT_PREFIX + msg_subj,
        msg_txt,
        settings.SERVER_EMAIL,          
        [a[1] for a in membership_managers],
        fail_silently=True
        )

def validate_membership( user ):
	# Funtion to automatically send a mail when a membership is validated
	username = user.username
	msg_to = user.email
	msg_from = "NO-REPLY@jebif.fr"
	msg_subj = u"Ton adhésion à JeBiF"
	msg_txt = u"""
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
		info_form = UserInfoForm()
		return render(request, 'jebif_users/register.html', {'user_form': user_form, 'info_form': info_form})

	def post(self, request):
		user_form = UserRegisterForm(request.POST)
		info_form = UserInfoForm(request.POST)

		if user_form.is_valid() and info_form.is_valid():
			#creation of User
			user = user_form.save()
			#creation of UserInfo
			user_info = info_form.save(commit=False)
			user_info.user = user
			user_info.email = user.email
			user_info.save()
			#if (user_info.want_member == True) and (settings.DEBUG == False):
			#	ask_membership()
			return redirect('home')
		else:
			return render(request, 'jebif_users/register.html', {'user_form': user_form, 'info_form': info_form})

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
	

@login_required
def profile_view(request):
	#Function for the profile page, to modify info
	user = request.user
	user_info = request.user.info  # get UserInfo linked to User
	today = datetime.date.today()
	remaining_time = (user_info.end_membership - today).days
	show_button_membership = user_info.end_membership and (remaining_time <= 30) and (user_info.is_member == False) and (user_info.want_member == False)
	

	if request.method == "POST":
		#user_form = UserRegisterForm(request.POST, instance=user)	# MAYBE CHANGE FORM, had a part to confirm old password
		user_form = UserModificationForm(request.POST, instance=request.user, user=request.user)
		info_form = UserInfoForm(request.POST, instance=user_info)
		if info_form.is_valid() and user_form.is_valid():
			user = user_form.save()
			user_info = info_form.save(commit=False)
			if user.email != user_info.email:
				user_info.email = user.email
			info_form.save()
			#if (user_info.is_member == False) and (user_info.want_member == True) and (settings.DEBUG == False):
			#	ask_membership()
			return redirect('profile')
	else:
		user_form = UserModificationForm(instance=user)		#retrieve the known info
		info_form = UserInfoForm(instance=user_info) 

	return render(request, 'jebif_users/profile.html', {'user_form': user_form, 'info_form': info_form, 'show_button_membership': show_button_membership, 'remaining_time': remaining_time,})
    

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
      

"""def subscription( request ) :
	if request.method == 'POST' :
		form = MembershipInfoForm(request.POST)
		if form.is_valid() :
			form.save()
			admin_url = f"http://jebif.fr{reverse('admin_subscription')}"
	
			msg_subj = "Demande d'adhésion"
			msg_txt = f"""#Bonjour,
            #Une demande d'adhésion vient d'être postée sur le site. Pour la modérer :
            #{admin_url}
"""
			membership_managers = getattr(settings, "MEMBERSHIP_MANAGERS", [])
			
			send_mail(
                settings.EMAIL_SUBJECT_PREFIX + msg_subj,
                msg_txt,
                settings.SERVER_EMAIL,          # MISSING IN SETTINGS?
                [a[1] for a in membership_managers],
                fail_silently=True
            )

			return redirect("subscription_ok")	# error here? need better url?
	else :
		form = MembershipInfoForm()

	return render(request, "jebif_users/subscription.html", {"form": form})"""


"""@login_required
def subscription_renew( req, info_id ) :
	info = UserInfo.objects.get(id=info_id)

	if info.user != req.user :
		path = quote(req.get_full_path())
		from django.contrib.auth import REDIRECT_FIELD_NAME
		login_url = settings.LOGIN_URL
		return redirect(f"{login_url}?{REDIRECT_FIELD_NAME}={path}")

	membership = info.latter_membership()

	today = datetime.date.today()

	if membership.date_begin >= today :
		return render(req, "jebif_users/subscription_renewed.html", {
			"membership" : membership})

	if req.method == 'POST' :
		form = MembershipInfoForm(req.POST, instance=info)
		if form.is_valid() :
			form.save()
			m = User(info=info)
			if membership.has_expired() :
				m.init_date(today)
				info.inscription_date = today
				info.active = True
				info.save()
			else :
				m.init_date(membership.date_end + datetime.timedelta(1))
			m.save()
			return render(req, "jebif_users/subscription_renewed.html", 
				{"membership" : m})
	else :
		form = MembershipInfoForm(instance=info)

	return render(req, "jebif_users/subscription_renew.html", 
		{"form": form, "membership": membership, "today": today})"""

"""@login_required
def subscription_update( req, info_id ) :
	info = UserInfo.objects.get(id=info_id)
	if info.user != req.user :
		path = quote(req.get_full_path())
		from django.contrib.auth import REDIRECT_FIELD_NAME
		login_url = settings.LOGIN_URL
		return redirect(f"{login_url}?{REDIRECT_FIELD_NAME}={path}")

	membership = info.latter_membership()

	if membership.has_expired() :
		return subscription_renew(req, info_id)

	old_email = info.email

	if req.method == 'POST' :
		form = MembershipInfoForm(req.POST, instance=info)
		if form.is_valid() :
			info = form.save()
			if info.user is not None :
				u = info.user
				if u.email != info.email :
					u.email = info.email
					u.save()
			if info.email != old_email :
				MembershipInfoEmailChange.objects.create(old_email=old_email, info=info)
			return render(req, "jebif_users/subscription_updated.html", {"membership" : membership})
	else :
		form = MembershipInfoForm(instance=info)

	return render(req, "jebif_users/subscription_update.html", 
		{"form": form, "membership": membership})"""


"""@login_required
def subscription_self_update( req ) :
	info = UserInfo.objects.get(user=req.user)
	return subscription_update(req, info.id)"""


"""def subscription_preupdate( req ) :
	if req.method == "POST" :
		form = MembershipInfoEmailForm(req.POST)
		if form.is_valid() :
			info = form.cleaned_data["email"]
			data = info.get_contact_data()
			msg_from = "NO-REPLY@jebif.fr"
			msg_to = [info.email]
			msg_subj = u"Ton adhésion à JeBiF"
			msg_txt = u"""
#Bonjour %(firstname)s,

#Tu peux modifier ton adhésion à l'association JeBiF en te rendant sur
#	%(url_update)s
#avec ton identifiant '%(login)s'%(passwd_setup)s.

#À bientôt,
#L’équipe JeBiF (RSG-France)
""" % data
			send_mail(msg_subj, msg_txt, msg_from, msg_to)
			return render(req, "jebif_users/subscription_preupdated.html",
					{"email" : info.email})
	else :
		form = MembershipInfoEmailForm()
	return render(req, "jebif_users/subscription_preupdate.html", {"form": form})
"""

def is_admin() :
	def validate( u ) :
		return u.is_authenticated() and u.is_staff
	return user_passes_test(validate)

@is_admin()
def admin_subscription( request ) :
	infos = UserInfo.objects.filter(is_active=False, is_deleted=False, membership=None)
	return render(request, "jebif_users/admin_subscription.html", {"infos": infos})

"""
@is_admin()
def admin_subscription_accept( request, info_id ) :
	with atomic() :
		info = UserInfo.objects.get(id=info_id)
		info.active = True
		info.inscription_date = datetime.date.today()
		m = Membership(info=info)
		m.init_date(info.inscription_date)
		m.save()
		info.save()

	msg_from = "NO-REPLY@jebif.fr"
	msg_to = [info.email]
	msg_subj = "Bienvenue dans l'association JeBiF"
	msg_txt = f"""
#Bonjour {info.firstname},

#Nous avons bien pris en compte ton adhésion à l’association JeBiF. N’hésite pas à nous contacter si tu as des questions, des commentaires, des idées, etc…

#Tu connais sans doute déjà notre site internet http://jebif.fr. Tu peux aussi faire un tour sur notre page internationale du RSG-France.
#http://www.iscbsc.org/rsg/rsg-france

#Tu vas être inscrit à la liste de discussion des membres de l’association. Tu pourras y consulter les archives si tu le souhaites.
#http://lists.jebif.fr/mailman/listinfo/membres

#À bientôt,
#L’équipe JeBiF (RSG-France)
"""
	send_mail(msg_subj, msg_txt, msg_from, msg_to)

	return HttpResponseRedirect("../../")


@is_admin()
def admin_subscription_reject( request, info_id ) :
	info = get_object_or_404(UserInfo, id=info_id)
	info.is_deleted = True
	info.save()
	return HttpResponseRedirect("../../")


@is_admin()
def admin_export_csv( request ) :
	charset = 'utf-8'
	response = HttpResponse(mimetype='text/csv')
	response['Content-Disposition'] = 'attachment; filename=membres_jebif.csv'

	writer = csv.writer(response)
	writer.writerow(['Nom', 'Prénom', 'E-mail',
		'Laboratoire', 'Ville', 'Pays', 'Poste actuel',
		'Motivation', 'Date inscription'])

	infos = UserInfo.objects.filter(active=True).extra(select={'ord':'lower(lastname)'}).order_by('ord')
	e = lambda s : s.encode(charset)
	for i in infos :
		writer.writerow(map(e, [i.lastname, i.firstname, 
			i.email, i.laboratory_name, i.laboratory_city,
			i.laboratory_country, i.position,
			i.motivation.replace("\r\n", " -- "),
			i.inscription_date.isoformat()]))

	return response
"""