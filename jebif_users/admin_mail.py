"""Module d'envoi de mails groupés par un admin (page admin du site).

Usage (vue admin) :
    from .admin_mail import (
        ADMIN_MAIL_GROUPS, send_group_mail, group_recipients, get_signature,
    )

    recipients = group_recipients(form.cleaned_data['recipients_group'])
    signature = get_signature(form.cleaned_data['signature'])
    send_group_mail(subject, body, recipients, signature=signature)

La signature (facultative) est choisie parmi celles enregistrées dans le
modèle ``MailSignature`` (admin Django) et est automatiquement ajoutée
à la fin du mail, avant l'envoi.

Le corps du mail et les signatures sont du texte riche (TinyMCE) : le mail
est envoyé en HTML, avec un repli texte brut pour les clients qui n'affichent
pas le HTML (``html_to_text``).
"""

import logging
import re

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from html import unescape    # stdlib (django.utils.html.unescape supprimé en Django 6.0)
from django.utils.html import strip_tags

#: Balise HTML (balise ouvrante/fermante avec un nom de balise en lettre)
_HTML_TAG_RE = re.compile(r"<\s*/?[a-zA-Z][^>]*>")


def has_html_tags(text):
    """Indique si ``text`` contient au moins une balise HTML.

    (``django.utils.html.find_html_tag`` n'existe plus en Django 6.0.)
    """
    return bool(text and _HTML_TAG_RE.search(text))

from .models import UserInfo, MailSignature

#: Valeur du choix "aucune signature" dans le formulaire
NO_SIGNATURE = "0"

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


def get_signature(signature_id=None):
    """Retourner la signature active pour l'identifiant ``signature_id``.

    ``signature_id`` peut être l'identifiant (int ou str) d'une
    ``MailSignature``, ``None``, la chaîne vide ou ``NO_SIGNATURE``
    (cas "aucune signature") : dans ces derniers cas, ``None`` est
    retourné. Une signature inexistante ou désactivée donne aussi
    ``None``.
    """
    if signature_id in (None, "", NO_SIGNATURE):
        return None
    try:
        pk = int(signature_id)
    except (TypeError, ValueError):
        return None
    return MailSignature.objects.filter(pk=pk, is_active=True).first()


def html_to_text(html):
    """Convertir du HTML en texte lisible (repli pour clients sans HTML).

    Les fins de blocs (paragraphes, listes, lignes, titres) deviennent des
    sauts de ligne, les balises sont retirées et les entités HTML décodées.
    Une chaîne sans balise est retournée telle quelle.
    """
    if html is None or not has_html_tags(html):
        return html or ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</?(?:p|div|li|tr|h[1-6])[^>]*>", "\n", text)
    text = strip_tags(text)
    text = unescape(text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def append_signature(body, html_body=None, signature=None):
    """Ajouter ``signature`` à la fin de ``body`` (et de ``html_body``).

    ``signature`` peut être du texte riche (HTML) : il est ajouté tel quel
    au corps HTML, et en version texte (``html_to_text``) au corps texte.

    Retourne le couple ``(body, html_body)`` modifié ; si ``signature``
    est ``None`` ou vide, rien n'est changé.
    """
    if signature is None:
        return body, html_body
    sig = signature.text.strip()
    if not sig:
        return body, html_body
    if has_html_tags(sig):
        sig_plain = html_to_text(sig)
        sig_html = sig
    else:
        sig_plain = sig
        sig_html = sig.replace("\n", "<br/>")
    if body is not None:
        body = f"{body.rstrip()}\n\n{sig_plain}"
    if html_body is not None:
        html_body = f"{html_body.rstrip()}\n{sig_html}"
    return body, html_body


def send_group_mail(subject, body, recipients, html_body=None, from_email=None,
                    signature=None):
    """Envoyer un e-mail au compte admin vers la liste ``recipients``.

    ``signature`` : instance ``MailSignature`` (ou son identifiant, ou
    ``None``) ; la signature est automatiquement ajoutée à la fin du
    message (corps texte, et corps HTML s'il y en a un). Le corps du
    message et la signature peuvent être du texte riche (HTML).

    Retourne le nombre de mails effectivement envoyés.
    """
    if not recipients:
        raise ValueError("La liste des destinataires est vide.")

    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    if not isinstance(signature, MailSignature):
        signature = get_signature(signature)
    body, html_body = append_signature(body, html_body, signature)

    msg = EmailMessage(
        subject=settings.EMAIL_SUBJECT_PREFIX + subject,
        body=body,
        from_email=from_email,
        to=list(recipients),
    )
    if html_body:
        # Django >= 6.0 : attach_alternative() a été supprimé, utiliser attach()
        msg.attach(filename=None, content=html_body, mimetype="text/html")

    count = msg.send()
    logger.info("Admin mail: %d recipient(s) for subject %r", len(recipients), subject)
    return count
