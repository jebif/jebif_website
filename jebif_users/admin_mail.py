"""Module d'envoi de mails groupés par un admin (page admin du site).

Usage (vue admin) :
    from .admin_mail import ADMIN_MAIL_GROUPS, send_group_mail, group_recipients

    recipients = group_recipients(form.cleaned_data['recipients_group'])
    send_group_mail(subject, body, recipients)
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import UserInfo

logger = logging.getLogger(__name__)


def _active_members():
    """Tous les membres actifs (adhésion valide et compte non supprimé)."""
    return UserInfo.objects.filter(
        is_member=True,
        is_deleted=False,
        end_membership__gte=timezone.localdate(),
    ).select_related("user")


def group_recipients(group_key):
    """Retourner la liste des destinataires (adresses e-mail) pour un groupe donné.

    Groups disponibles (voir ``ADMIN_MAIL_GROUPS``) :
    - ``members_active``  : adhérents avec une adhésion active
    - ``all_users``       : tous les comptes non supprimés
    - ``staff``           : comptes staff/admin
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    if group_key == "members_active":
        return [i.email for i in _active_members() if i.email]
    if group_key == "all_users":
        return [i.email for i in UserInfo.objects.exclude(is_deleted=True).select_related("user") if i.email]
    if group_key == "staff":
        return [u.email for u in User.objects.filter(is_staff=True) if u.email]
    raise KeyError(f"Unknown recipients group: {group_key!r}")


#: Choix proposés dans le formulaire (valeur, libellé)
ADMIN_MAIL_GROUPS = (
    ("members_active", "Tous les adhérents (adhésion active)"),
    ("all_users", "Tous les utilisateurs inscrits (non supprimés)"),
    ("staff", "Tous les administrateurs (staff)"),
)


def send_group_mail(subject, body, recipients, html_body=None, from_email=None):
    """Envoyer un e-mail au compte admin vers la liste ``recipients``.

    Retourne le nombre de mails effectivement envoyés.
    """
    if not recipients:
        raise ValueError("La liste des destinataires est vide.")

    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    msg = EmailMessage(
        subject=settings.EMAIL_SUBJECT_PREFIX + subject,
        body=body,
        from_email=from_email,
        to=list(recipients),
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")

    count = msg.send()
    logger.info("Admin mail: %d recipient(s) for subject %r", len(recipients), subject)
    return count
