from django.views import View

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth.decorators import login_required, user_passes_test

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db.transaction import atomic
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse

import binascii
import csv
import datetime
from pathlib import Path

from .models import *
from .forms import *

from django.http import JsonResponse
from jebif_website.models import Events, Meetings

# Get emails from "Staff" users.
User = get_user_model()


def get_staff_emails():
    """Emails of "Staff" users.
    Computed at call time (a query at import time breaks `manage.py check`
    and freezes the list for the life of the process).
    """
    return [user.email for user in User.objects.filter(is_staff=True) if user.email]


# ---- Verification link tokens ---------------------------------------------
# The token is a HMAC-signed, timestamped string (django.core.signing):
# it cannot be forged without the SECRET_KEY and expires after 24 hours.
_verify_signer = TimestampSigner(salt="jebif-user-verification")
VERIFY_TOKEN_MAX_AGE = 60 * 60    # 1 hour


def make_verify_token(user):
    return _verify_signer.sign_object(str(user.pk))


def validate_verify_token(token, uid):
    """Check that `token` is a fresh, valid signature for the user with pk `uid`."""
    try:
        payload = _verify_signer.unsign_object(token, max_age=VERIFY_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired, binascii.Error, ValueError, TypeError):
        # Malformed / forged / expired token: treat as invalid, never crash
        return False
    return str(payload) == str(uid)


def ask_membership():
    # Function to automatically send a mail to check the membership (new and renew)
    msg_subj = "Demande d'adhésion"
    admin_url = f"{settings.HTTP_DOMAIN}/admin/auth/user/" 

    msg_txt = f"""Bonjour,
            Une demande d'adhésion ou de ré-adhésion vient d'être postée sur le site. Pour l'accepter' :
            {admin_url}"""
            
    send_mail(
         subject=settings.EMAIL_SUBJECT_PREFIX + msg_subj,
         message=msg_txt,
         from_email=settings.DEFAULT_FROM_EMAIL,
         recipient_list=get_staff_emails(),
         fail_silently=True
         )

def resend_validation_mail(request):
    # Renvoyer le mail de vérification (uniquement pour l'utilisateur connecté)
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method == "POST":
        user_info = UserInfo.objects.filter(user=request.user).first()
        if user_info and user_info.verified:
            messages.info(request, "Ton compte est déjà vérifié.")
            return redirect("profile")

        adhere = bool(user_info.want_member) if user_info else False
        send_validation_mail(request.user, adhere)
        messages.success(request, "✅ Un nouveau mail de vérification t'a été envoyé.")
        return redirect("profile")

    return redirect("profile")

def send_validation_mail(user, adhere: bool):
    token = make_verify_token(user)
    domain = settings.HTTP_DOMAIN

    send_mail(
        subject=settings.EMAIL_SUBJECT_PREFIX + "Creation de compte JeBiF",
        message=f"""
Bonjour {user.username},

Ton compte sur le site de l'association JeBiF vient d'être créé, mais il n'est pas encore actif.
Pour vérifier ton adresse mail, clique sur ce lien (valable 24 heures) : {domain}/users/verify/{user.pk}/{token}_{adhere}

Une fois ton adresse-mail validée, la demande d'adhésion sera transmise au conseil d'administration qui 
la considèrera lors de sa prochaine réunion.

À bientôt,
L’équipe JeBiF (RSG-France)
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False
        )

class RegisterView(View):
    #View to create a new User
    def get(self, request):
        user_form = UserRegisterForm()
        return render(request, 'jebif_users/register.html', {'user_form': user_form})

    def post(self, request):
        
        user_form = UserRegisterForm(request.POST)
        
        if user_form.is_valid():
            with atomic() :
                #creation of User + empty (unverified) UserInfo
                user = user_form.save()
                UserInfo.objects.create(
                    user=user,
                    email=user.email,
                    want_member=False,
                    verified=False,
                )
                messages.success(request, "✅ Ton compte a été créé, tu as reçu un mail avec un lien pour confirmer ton inscription.")
            
            send_validation_mail(user, False)
            
            return redirect('home')
        else:
            messages.error(request, "⚠️ Il y a une ou plusieurs erreur(s) dans le formulaire, merci de les corriger.")
            return render(request, 'jebif_users/register.html', {'user_form': user_form})

class AdhesionView(View):
    def get(self, request):
        user_form = UserRegisterForm()
        info_form = UserInfoForm()
        return render(request, 'jebif_users/adhesion.html', {'user_form': user_form, 'info_form': info_form})
    
    def post(self, request):
        user_form = UserRegisterForm(request.POST)
        info_form = UserInfoForm(request.POST)
        
        if user_form.is_valid() and info_form.is_valid():
            with atomic() :
                #creation of User + UserInfo (unverified, requesting membership)
                user = user_form.save()
                user_info = info_form.save(commit=False)
                user_info.user = user
                user_info.email = user.email
                user_info.want_member = True
                user_info.verified = False
                user_info.save()

                messages.success(request, "✅ Ton compte a été créé, tu as reçu un mail avec un lien pour confirmer ton inscription.")

            send_validation_mail(user, True)
            return redirect('home')
        else:
            messages.error(request, "⚠️ Il y a une ou plusieurs erreur(s) dans le formulaire, merci de les corriger.")
            return render(request, 'jebif_users/adhesion.html', {'user_form': user_form, 'info_form': info_form})


class CustomLoginView(LoginView):
    template_name = 'jebif_users/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.error(
                request,
                f"⚠️ Vous êtes déjà connecté avec le compte \"{request.user.username}\". Si vous tentiez d'accéder à une page, vous n'avez pas les droits pour accéder à cette page."
            )
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    # def form_valid(self, form):       #Prefer allowing the User to connect. the user gets a banner telling it to verify its account
    #     user = form.get_user()
    #     if hasattr(user, 'info') and (user.is_superuser or user.info.verified): 
    #         return super().form_valid(form)
    #     else:
    #         form.add_error(None, "⚠️ Vous n'avez pas confirmé votre inscription via le mail que vous avez reçu. <a href=''>Renvoyer le mail de validation</a>")
    #         return self.form_invalid(form)


class CustomPasswordResetView(PasswordResetView):
    template_name = 'jebif_users/password_reset.html'
    email_template_name = 'jebif_users/password_reset_email.html'
    subject_template_name = 'jebif_users/password_reset_subject.txt'
    success_url = '/users/password_reset/done/'
    extra_email_context = {
        "site_name": "[JeBiF]",
    }

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = User.objects.filter(email=email).first()
        if user:
            messages.success(self.request, "✅ Si un compte existe avec cet email, un message a été envoyé.")
            return super().form_valid(form)
        else:
            form.add_error(None, "Il n'existe pas de compte avec cette adresse email.")
            return self.form_invalid(form)


def _import_old_account(user, user_info):
    """If the user's email is in fixtures.csv (old site), pre-fill user_info
    with the imported membership data. Return True if an account was found."""
    fixtures_file = Path(__file__).parent.joinpath("fixtures.csv")
    if not fixtures_file.exists():
        return False

    try:
        with open(fixtures_file, "r", encoding="utf-8") as f:
            for account in csv.DictReader(f, delimiter=","):
                if account.get("email") != user.email:
                    continue

                try:
                    inscription = datetime.date.fromisoformat(account["inscription_date"])
                except (KeyError, TypeError, ValueError):
                    continue

                user_info.firstname = account.get("firstname") or ""
                user_info.lastname = account.get("lastname") or ""
                user_info.laboratory = account.get("laboratory_name") or ""
                user_info.city_name = account.get("laboratory_city") or ""
                user_info.city_cp = ""
                user_info.country = account.get("laboratory_country") or ""
                user_info.position = account.get("position") or ""
                user_info.motivation = account.get("motivation") or ""
                user_info.inscription_date = inscription
                user_info.is_member = account.get("active", "False")
                user_info.want_member = False
                user_info.is_deleted = account.get("deleted", "False")
                user_info.begin_membership = inscription
                user_info.end_membership = user_info.get_end_membership(inscription)
                user_info.know_from = "Déjà adhérent"
                return True
    except (OSError, csv.Error):
        pass
    return False


class VerifyView(View):
    # The token (HMAC-signed + timestamped) MUST be validated before any
    # action: it is the only proof that the requester owns the mailbox.
    def _get_user(self, uid):
        try:
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

    def _invalid_link(self, request):
        messages.error(request, "⚠️ Lien de vérification invalide ou expiré. Connecte-toi pour demander un nouveau mail de vérification.")
        return redirect("home")

    def get(self, request, uid, token, adhere=False):
        user = self._get_user(uid)
        if user is None or not validate_verify_token(token, uid):
            return self._invalid_link(request)

        user_info = UserInfo.objects.filter(user=user).first()
        if user_info and user_info.verified:
            messages.info(request, "Ce compte est déjà vérifié, connecte-toi.")
            return redirect("login")

        existing_account = False
        if user_info is None:
            user_info = UserInfo(
                user=user,
                email=user.email,
                want_member=(adhere == "True"),
            )
            existing_account = _import_old_account(user, user_info)
            user_info.save()

        info_form = UserInfoForm(instance=user_info)
        return render(request, "jebif_users/fill_info.html", {"existing_account":existing_account, "info_form":info_form})

    def post(self, request, uid, token, adhere):
        user = self._get_user(uid)
        if user is None or not validate_verify_token(token, uid):
            return self._invalid_link(request)

        user_info = UserInfo.objects.filter(user=user).first()
        if user_info:
            info_form = UserInfoForm(request.POST, instance=user_info)
            existing_account = True
        else:
            info_form = UserInfoForm(request.POST)
            existing_account = False

        if info_form.is_valid():
            with atomic():
                user_info = info_form.save(commit=False)
                user_info.user = user
                user_info.email = user.email
                user_info.want_member = (adhere == "True")
                user_info.verified = True
                user_info.save()

                if user_info.want_member:
                    bonus = "Ton adhésion est en cours d'évaluation par le Conseil d'Administration."
                elif existing_account:
                    bonus = "Ton adhésion a été transférée depuis l'ancien site."
                else:
                    bonus = ""
                messages.success(request, f"✅ Tes informations ont été enregistrées. {bonus}".rstrip())

            auth_login(request, user)
            return redirect("profile")
        else:
            messages.error(request, "⚠️ Il y a une ou plusieurs erreur(s) dans le formulaire, merci de les corriger.")
            return render(request, "jebif_users/fill_info.html", {"existing_account":existing_account, "info_form":info_form})


@login_required
def profile_view(request):
    #Function for the profile page, to modify info
    user = request.user

    today = datetime.date.today()

    try:
        user_info = request.user.info  # get UserInfo linked to User
    except(TypeError, ValueError, OverflowError, User.info.RelatedObjectDoesNotExist):
        messages.error(request, "⚠️ Ton profil est incomplet, contacte un administrateur.")
        return redirect("home")

    remaining_time = (user_info.end_membership - today).days

    show_ask_membership = (user_info.want_member == False) and (user_info.is_member == False)
    
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
        user_form = UserModificationForm(instance=user)        #retrieve the known info
        info_form = UserInfoForm(instance=user_info)

    return render(request, 'jebif_users/profile.html', {'user_form': user_form, 'info_form': info_form, 'show_ask_membership': show_ask_membership, 'remaining_time': remaining_time,})

@login_required
def request_membership(request):
    #Function for user to request the membership
    user_info: UserInfo = getattr(request.user, "info", None)
    if not user_info.is_complete():
        messages.error(request, "⚠️ Ton profil est incomplet, remplis tous les champs avec * pour pouvoir demander l'adhésion.")
        return redirect("profile")

    if request.method == "POST":
        user_info.want_member = True
        user_info.save()
        if settings.DEBUG == False:
            ask_membership() #function to send a mail to admin
        messages.success(request, "✅ Ta demande d'adhésion a bien été envoyée à l'association!")
    return redirect('profile')

@login_required
def stop_membership_reminder(request):
    user_info: UserInfo = getattr(request.user, "info", None)
    user_info.stop_membership_reminder = True
    user_info.save()
    return redirect(request.GET.get("next", "home"))

@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        # Log out (clear the session) BEFORE deleting the user from the database
        auth_logout(request)
        user.delete()
    return redirect("home")

def is_admin() :
    def validate( u ) :
        return u.is_authenticated and u.is_staff
    return user_passes_test(validate)

@login_required
@is_admin()
def button_admin(request):
    if not (request.user or request.user.info.is_member or request.user.is_superuser):  
        #won't work, the decorator will always redirect first because of user_passes_test.
        messages.error(request, "❌ Vous n'avez pas accès à cette page.")
        return redirect("/")
    if request.method == 'POST':
        return redirect('admin_home')
    else:
        return render(request, 'jebif_users/button_admin.html')

@login_required   
@is_admin()
def admin_home_view(request): 
    return render(request, 'jebif_users/admin_home.html')

@login_required
@is_admin()
def admin_subscription( request ) :
    infos = UserInfo.objects.filter(is_member=False, is_deleted=False, want_member=True)
    return render(request, "jebif_users/admin_subscription.html", {"infos": infos})

@login_required
@is_admin()
def admin_subscription_accept( request, info_id ) :
    #Function for the admin page in the website (not the interface) to accept subscription.
    #POST only: a state-changing action must not be reachable with a plain GET link (CSRF).
    if request.method != "POST":
        return redirect("admin_subscription")

    info = get_object_or_404(UserInfo, id=info_id)
    if info.is_member:
        messages.info(request, "Cette adhésion est déjà acceptée.")
        return redirect("admin_subscription")

    with atomic() :
        info.is_member = True
        info.want_member = False
        info.inscription_date = datetime.date.today()
        info.init_date(info.inscription_date)
        info.save()

    msg_to = [info.email]
    msg_subj = "Bienvenue dans l'association JeBiF"
    msg_txt = f"""

Bonjour {info.firstname},

Nous avons bien pris en compte ton adhésion à l’association JeBiF. N’hésite pas à nous contacter si tu as des questions, des commentaires, des idées, etc…

Tu connais sans doute déjà notre site internet https://jebif.fr. Tu peux aussi faire un tour sur notre page internationale du RSG-France.
https://www.iscbsc.org/rsg/rsg-france

À bientôt,
L’équipe JeBiF (RSG-France)
"""
    send_mail(msg_subj, msg_txt, settings.DEFAULT_FROM_EMAIL, msg_to)

    messages.success(request, "✅ Adhésion acceptée.")
    return redirect("admin_subscription")

@login_required
@is_admin()
def admin_subscription_reject( request, info_id ) :
    #Function for the admin page in the website (not the interface) to reject subscription.
    if request.method != "POST":
        return redirect("admin_subscription")

    info = get_object_or_404(UserInfo, id=info_id)
    if not info.want_member:
        messages.info(request, "Cette demande est déjà refusée.")
        return redirect("admin_subscription")

    info.want_member = False
    info.save()

    messages.success(request, "✅ Demande d'adhésion refusée.")
    return redirect("admin_subscription")

@login_required
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
            (i.motivation or "").replace("\r\n", " -- "),
            i.inscription_date.isoformat()])

    return response

@login_required
@is_admin()
def admin_calendar(request):
    if not (request.user.is_authenticated and request.user.info.is_member and request.user.is_superuser):
        messages.error(request, "❌ Vous n'avez pas accès à cette page.")
        return redirect("/")
    return render(request, "jebif_users/admin_calendar.html")


@login_required
@is_admin()
def events_json(request):
    data = []
    events = Events.objects.all()
    # Events like JebifPub
    for e in events:
        data.append({
            "title": f"EV : {e.title}",
            "start": e.date.date().isoformat(),
            "description": e.description,
            "localisation": e.localisation,
            "max_participants": e.max_participants,
            "allDay": True,#Need to change this; end = start +1h
            "color": "blue",
        })

    # Meetings
    for m in Meetings.objects.all():
        data.append({
            "title": f"{m.kind} : {m.title}",
            "start": m.date.date().isoformat(),
            "description": m.description,
            "allDay": True,
            "color": m.color,
        })

    return JsonResponse(data, safe=False)
    
@login_required
def user_calendar(request):
    if not (request.user.is_authenticated and request.user.info.is_member):
        messages.error(request, "❌ Vous n'avez pas accès à cette page.")
        return redirect("/")
    return render(request, "jebif_users/user_calendar.html")