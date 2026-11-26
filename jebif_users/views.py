from django.views import View

from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth.decorators import login_required, user_passes_test

from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db.models.functions import Lower
from django.db.transaction import atomic
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.http import JsonResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.views.decorators.http import require_POST

import binascii
import csv
import datetime
from pathlib import Path

from jebif_website.utils import get_staff_emails, send_mail_safe, hit_rate_limit
from .models import UserInfo, end_membership
from .forms import UserRegisterForm, UserModificationForm, UserInfoForm, FillInfoForm
from jebif_website.models import Events, Meetings


User = get_user_model()


# ---- Verification link tokens ---------------------------------------------
_verify_signer = TimestampSigner(salt="jebif-user-verification")
VERIFY_TOKEN_MAX_AGE = 24 * 60 * 60    # 24 hours (the e-mail says so)
RESEND_VERIFY_DELAY = 60               # seconds between two "resend" requests


def make_verify_token(user, adhere):
    return _verify_signer.sign_object({"uid": user.pk, "email": user.email, "adhere": bool(adhere)})


def read_verify_token(token):
    """Return the payload of a fresh, valid token, or None."""
    try:
        payload = _verify_signer.unsign_object(token, max_age=VERIFY_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired, binascii.Error, ValueError, TypeError):
        # Malformed / forged / expired token: treat as invalid, never crash
        return None
    if not isinstance(payload, dict) or not {"uid", "email", "adhere"} <= payload.keys():
        return None
    return payload


def ask_membership():
    # Function to automatically send a mail to check the membership (new and renew)
    admin_url = f"{settings.HTTP_DOMAIN}{reverse('admin_subscription')}"
    msg_txt = f"""Bonjour,

Une demande d'adhésion ou de ré-adhésion vient d'être postée sur le site. Pour l'accepter :
{admin_url}"""
    send_mail_safe(settings.EMAIL_SUBJECT_PREFIX + "Demande d'adhésion", msg_txt, get_staff_emails())


def send_validation_mail(user, adhere: bool):
    """Send the e-mail address verification link. Returns True if the mail was sent."""
    token = make_verify_token(user, adhere)
    link = settings.HTTP_DOMAIN + reverse("verify", kwargs={"token": token})
    return send_mail_safe(
        settings.EMAIL_SUBJECT_PREFIX + "Vérification de ton adresse e-mail",
        f"""
Bonjour {user.username},

Ton compte sur le site de l'association JeBiF vient d'être créé ou modifié, mais ton adresse e-mail n'est pas encore vérifiée.
Pour vérifier ton adresse mail, clique sur ce lien (valable 24 heures) : {link}

Si tu as demandé à adhérer, une fois ton adresse-mail validée, la demande d'adhésion sera transmise
au conseil d'administration qui la considèrera lors de sa prochaine réunion.

À bientôt,
L’équipe JeBiF (RSG-France)
""",
        [user.email],
    )


def _validation_mail_message(request, sent):
    if sent:
        messages.success(request, "✅ Un mail avec un lien pour confirmer ton adresse t'a été envoyé.")
    else:
        messages.warning(request, "⚠️ Le mail de vérification n'a pas pu être envoyé. Connecte-toi et utilise le lien « Renvoyer le mail de validation », ou contacte-nous.")


@login_required
@require_POST
def resend_validation_mail(request):
    # Resend the verification mail (only for the logged-in user, POST only, rate limited)
    user_info = UserInfo.objects.filter(user=request.user).first()
    if user_info and user_info.verified:
        messages.info(request, "Ton compte est déjà vérifié.")
        return redirect("profile")

    if hit_rate_limit("resend_verify", request.user.pk, RESEND_VERIFY_DELAY):
        messages.error(request, "Un mail vient déjà d'être envoyé, réessaie dans une minute.")
        return redirect("profile")

    adhere = bool(user_info.want_member) if user_info else False
    _validation_mail_message(request, send_validation_mail(request.user, adhere))
    return redirect("profile")


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
            messages.success(request, "✅ Ton compte a été créé.")
            _validation_mail_message(request, send_validation_mail(user, False))
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

            messages.success(request, "✅ Ton compte a été créé.")
            _validation_mail_message(request, send_validation_mail(user, True))
            return redirect('home')
        else:
            messages.error(request, "⚠️ Il y a une ou plusieurs erreur(s) dans le formulaire, merci de les corriger.")
            return render(request, 'jebif_users/adhesion.html', {'user_form': user_form, 'info_form': info_form})


class CustomLoginView(LoginView):
    template_name = 'jebif_users/login.html'

    def dispatch(self, request, *args, **kwargs):
        # Already logged in: usually sent here by a page this account cannot access
        if request.user.is_authenticated:
            messages.error(
                request,
                f"⚠️ Tu es déjà connecté·e avec le compte \"{request.user.username}\". "
                "Si tu tentais d'accéder à une page, ce compte n'a pas les droits nécessaires."
            )
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    # Same message whether an account exists or not: the page must not reveal
    # which e-mail addresses are registered.
    template_name = 'jebif_users/password_reset.html'
    email_template_name = 'jebif_users/password_reset_email.html'
    subject_template_name = 'jebif_users/password_reset_subject.txt'
    success_url = '/users/password_reset/done/'
    extra_email_context = {
        "site_name": "[JeBiF]",
    }

    def form_valid(self, form):
        messages.success(self.request, "✅ Si un compte existe avec cet email, un message a été envoyé.")
        return super().form_valid(form)


def _parse_bool(value):
    return str(value).strip().lower() in ("true", "1", "yes", "oui")


def _membership_end_after(inscription, today=None):
    """End of the current yearly membership period that started on `inscription`
    (the anniversary is kept, so an old membership is not considered expired
    just because it started several years ago)."""
    today = today or datetime.date.today()
    start = inscription
    end = end_membership(start)
    while end < today:
        start = end + datetime.timedelta(1)
        end = end_membership(start)
    return start, end


def _import_old_account(user, user_info):
    """If the user's email is in fixtures.csv (old site), pre-fill user_info
    with the imported membership data. Return True if an account was found."""
    fixtures_file = Path(__file__).parent.joinpath("fixtures.csv")
    if not fixtures_file.exists():
        return False

    try:
        with open(fixtures_file, "r", encoding="utf-8") as f:
            for account in csv.DictReader(f, delimiter=","):
                if (account.get("email") or "").strip().lower() != user.email.lower():
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
                user_info.is_member = _parse_bool(account.get("active", "False"))
                user_info.want_member = False
                user_info.is_deleted = _parse_bool(account.get("deleted", "False"))
                user_info.begin_membership, user_info.end_membership = _membership_end_after(inscription)
                user_info.know_from = "Déjà adhérent"
                return True
    except (OSError, csv.Error):
        pass
    return False


class VerifyView(View):
    # The token (HMAC-signed + timestamped) MUST be validated before any
    # action: it is the only proof that the requester owns the mailbox.
    # The link is single-use: once the account is verified, it stops working.
    def _check(self, token):
        """Return (user, payload) if the link is valid and still usable, else None."""
        payload = read_verify_token(token)
        if payload is None:
            return None
        user = User.objects.filter(pk=payload["uid"], is_active=True).first()
        # The link is only valid for the address it was sent to
        if user is None or user.email.lower() != str(payload["email"]).lower():
            return None
        return user, payload

    def _invalid_link(self, request):
        messages.error(request, "⚠️ Lien de vérification invalide ou expiré. Connecte-toi pour demander un nouveau mail de vérification.")
        return redirect("home")

    def get(self, request, token):
        checked = self._check(token)
        if checked is None:
            return self._invalid_link(request)
        user, payload = checked

        user_info = UserInfo.objects.filter(user=user).first()
        if user_info and user_info.verified:
            messages.info(request, "Ce compte est déjà vérifié, connecte-toi.")
            return redirect("login")

        existing_account = False
        if user_info is None:
            user_info = UserInfo(
                user=user,
                email=user.email,
                want_member=payload["adhere"],
            )
            existing_account = _import_old_account(user, user_info)
            user_info.save()

        info_form = self._fill_info_form(user_info, payload)
        return render(request, "jebif_users/fill_info.html", {"existing_account":existing_account, "info_form":info_form})

    @staticmethod
    def _fill_info_form(user_info, payload, data=None):
        """Info form, with the "request membership" checkbox (unless already an active member).
        The box is pre-checked if the membership was asked at registration (adhesion page)."""
        can_ask = not (user_info and user_info.is_active_member)
        initial = {"ask_membership": bool(payload["adhere"] or (user_info and user_info.want_member))}
        return FillInfoForm(data, instance=user_info, initial=initial, can_ask_membership=can_ask)

    def post(self, request, token):
        checked = self._check(token)
        if checked is None:
            return self._invalid_link(request)
        user, payload = checked

        user_info = UserInfo.objects.filter(user=user).first()
        if user_info and user_info.verified:
            # Single use: a verified account cannot be modified (nor logged into) with this link
            messages.info(request, "Ce compte est déjà vérifié, connecte-toi.")
            return redirect("login")

        existing_account = user_info is not None
        info_form = self._fill_info_form(user_info, payload, request.POST)

        if info_form.is_valid():
            with atomic():
                user_info = info_form.save(commit=False)
                user_info.user = user
                user_info.email = user.email
                if "ask_membership" in info_form.fields:
                    user_info.want_member = info_form.cleaned_data["ask_membership"]
                user_info.verified = True
                user_info.save()

            if user_info.want_member:
                bonus = "Ton adhésion est en cours d'évaluation par le Conseil d'Administration."
                ask_membership()
            elif existing_account and user_info.is_member:
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

    user_info = getattr(user, "info", None)  # UserInfo linked to User (may not exist, e.g. superuser)
    if user_info is None:
        messages.error(request, "⚠️ Ton profil est incomplet, contacte un administrateur.")
        return redirect("home")

    remaining_time = (user_info.end_membership - today).days
    show_button_membership = (user_info.want_member == False) and ((remaining_time <= 30) or (user_info.is_member == False))

    if request.method == "POST":
        user_form = UserModificationForm(request.POST, instance=user, user=user)
        info_form = UserInfoForm(request.POST, instance=user_info)
        if info_form.is_valid() and user_form.is_valid():
            email_changed = user_form.email_changed()
            with atomic():
                user = user_form.save()
                user_info = info_form.save(commit=False)
                user_info.email = user.email
                if email_changed:
                    # The new address must be verified again
                    user_info.verified = False
                user_info.save()

            if user_form.password_changed():
                # Changing the password invalidates the session: keep the user logged in
                update_session_auth_hash(request, user)
            messages.success(request, "✅ Tes informations ont été mises à jour.")
            if email_changed:
                _validation_mail_message(request, send_validation_mail(user, user_info.want_member))
            return redirect('profile')
        messages.error(request, "⚠️ Il y a une ou plusieurs erreur(s) dans le formulaire, merci de les corriger.")
    else:
        user_form = UserModificationForm(instance=user, user=user)        #retrieve the known info
        info_form = UserInfoForm(instance=user_info)

    return render(request, 'jebif_users/profile.html', {'user_form': user_form, 'info_form': info_form, 'show_button_membership': show_button_membership, 'remaining_time': remaining_time,})


@login_required
@require_POST
def request_membership(request):
    #Function for user to request the membership
    user_info = getattr(request.user, "info", None)
    if user_info is None:
        messages.error(request, "⚠️ Ton profil est incomplet, contacte un administrateur.")
        return redirect("home")

    if not user_info.verified:
        messages.error(request, "⚠️ Vérifie d'abord ton adresse e-mail (lien envoyé par mail) avant de demander l'adhésion.")
        return redirect("profile")

    if not user_info.is_complete():
        messages.error(request, "⚠️ Ton profil est incomplet, remplis tous les champs avec * pour pouvoir demander l'adhésion.")
        return redirect("profile")

    if not user_info.want_member:
        user_info.want_member = True
        user_info.save()
        ask_membership() #function to send a mail to admin
    messages.success(request, "✅ Ta demande d'adhésion a été transmise.")
    return redirect('profile')


@login_required
@require_POST
def stop_membership_reminder(request):
    # "Ne plus me le rappeler" on the membership banner
    user_info = getattr(request.user, "info", None)
    if user_info is not None:
        user_info.stop_membership_reminder = True
        user_info.save(update_fields=["stop_membership_reminder"])
        messages.info(request, "Le rappel ne sera plus affiché. Tu peux toujours demander l'adhésion depuis ton profil.")
    # Only redirect to a page of this site (no open redirect)
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = reverse("home")
    return redirect(next_url)


@login_required
@require_POST
def delete_account(request):
    user = request.user
    # Log out (clear the session) BEFORE deleting the user from the database
    auth_logout(request)
    user.delete()
    messages.success(request, "Ton compte a été supprimé.")
    return redirect("home")


def is_admin() :
    def validate( u ) :
        return u.is_authenticated and u.is_staff
    return user_passes_test(validate)


def can_manage_members() :
    # Accepting members and exporting their personal data needs the
    # "change userinfo" permission, not only the staff status
    def validate( u ) :
        return u.is_authenticated and u.is_staff and u.has_perm("jebif_users.change_userinfo")
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

@can_manage_members()
def admin_subscription( request ) :
    # New memberships and renewals (members asking to renew before/after the expiration)
    infos = UserInfo.objects.filter(is_deleted=False, want_member=True, verified=True)
    return render(request, "jebif_users/admin_subscription.html", {"infos": infos})


@can_manage_members()
@require_POST
def admin_subscription_accept( request, info_id ) :
    #Function for the admin page in the website (not the interface) to accept subscription.
    #POST only: a state-changing action must not be reachable with a plain GET link (CSRF).
    info = get_object_or_404(UserInfo, id=info_id)
    if not info.want_member:
        messages.info(request, "Cette demande a déjà été traitée.")
        return redirect("admin_subscription")

    renewal = info.is_active_member
    with atomic() :
        if renewal:
            # Renewal before the expiration: the new year starts at the end of the current one
            info.init_date(info.end_membership + datetime.timedelta(days=1))
        else:
            info.init_date(datetime.date.today())
        info.is_member = True
        info.want_member = False
        info.save()

    msg_txt = f"""

Bonjour {info.firstname},

Nous avons bien pris en compte ton adhésion à l’association JeBiF. N’hésite pas à nous contacter si tu as des questions, des commentaires, des idées, etc…

Tu connais sans doute déjà notre site internet https://jebif.fr. Tu peux aussi faire un tour sur notre page internationale du RSG-France.
https://www.iscbsc.org/rsg/rsg-france

À bientôt,
L’équipe JeBiF (RSG-France)
"""
    sent = send_mail_safe(settings.EMAIL_SUBJECT_PREFIX + "Bienvenue dans l'association JeBiF", msg_txt, [info.email])

    messages.success(request, "✅ Adhésion acceptée.")
    if not sent:
        messages.warning(request, f"⚠️ Le mail de bienvenue n'a pas pu être envoyé à {info.email}.")
    return redirect("admin_subscription")


@can_manage_members()
@require_POST
def admin_subscription_reject( request, info_id ) :
    #Function for the admin page in the website (not the interface) to reject subscription.
    #The account itself is kept (it is not marked as deleted): only the request is refused.
    info = get_object_or_404(UserInfo, id=info_id)
    if not info.want_member:
        messages.info(request, "Cette demande a déjà été traitée.")
        return redirect("admin_subscription")

    info.want_member = False
    info.save()

    msg_txt = f"""
Bonjour {info.firstname},

Ta demande d'adhésion à l'association JeBiF n'a pas été acceptée par le conseil d'administration.
N'hésite pas à nous contacter (https://jebif.fr/contact_form/) si tu as des questions.

L’équipe JeBiF (RSG-France)
"""
    send_mail_safe(settings.EMAIL_SUBJECT_PREFIX + "Ta demande d'adhésion à JeBiF", msg_txt, [info.email])

    messages.success(request, "✅ Demande d'adhésion refusée.")
    return redirect("admin_subscription")


def csv_safe(value):
    """Neutralise spreadsheet formulas (CSV injection): a cell starting with
    = + - @ (or tab / carriage return) is executed by Excel/LibreOffice."""
    value = "" if value is None else str(value)
    if value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@can_manage_members()
def admin_export_csv( request ) :
    #Function for the admin page in the website (not the interface) to export the list of members
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename=membres_jebif.csv'

    writer = csv.writer(response) # add (,delimiter=';') to change the delimiter
    writer.writerow(['Nom', 'Prénom', 'E-mail',
        'Laboratoire', 'Ville', 'Pays', 'Poste actuel',
        'Motivation', 'Date inscription'])

    infos = UserInfo.objects.filter(is_member=True, is_deleted=False).order_by(Lower("lastname"))

    for i in infos :
        writer.writerow([csv_safe(v) for v in (
            i.lastname, i.firstname,
            i.email, i.laboratory, i.city_name,
            i.country, i.position,
            (i.motivation or "").replace("\r\n", " -- "),
            i.inscription_date.isoformat())])

    return response


# ---- Calendar (events + staff meetings) ----

def _can_see_calendar(user):
    info = getattr(user, "info", None)
    return user.is_staff or bool(info and info.is_active_member)


@login_required
@is_admin()
def admin_calendar(request):
    # Staff page to add events and meetings (same permission as the creation endpoints)
    return render(request, "jebif_users/admin_calendar.html")


@login_required
def user_calendar(request):
    if not _can_see_calendar(request.user):
        messages.error(request, "❌ Le calendrier est réservé aux adhérent·e·s.")
        return redirect("home")
    return render(request, "jebif_users/user_calendar.html")


@login_required
def events_json(request):
    # Data of both calendars: members (user_calendar) and staff (admin_calendar)
    if not _can_see_calendar(request.user):
        return JsonResponse({"error": "Accès refusé"}, status=403)

    events = Events.objects.all()
    if not request.user.is_staff:
        # Members only see the validated events
        events = events.filter(active=True, pending=False)

    data = []
    for e in events:
        data.append({
            "title": f"EV : {e.title}",
            "start": timezone.localdate(e.date).isoformat(),
            "description": e.description,
            "localisation": e.localisation,
            "max_participants": e.max_participants,
            "allDay": True,
            "color": "blue",
        })
    for m in Meetings.objects.all():
        data.append({
            "title": f"{m.kind} : {m.title}",
            "start": timezone.localdate(m.date).isoformat(),
            "description": m.description,
            "allDay": True,
            "color": m.color,
        })
    return JsonResponse(data, safe=False)
