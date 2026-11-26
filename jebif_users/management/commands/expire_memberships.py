"""
Daily job: expire memberships that have passed their end_membership date,
and send reminder mails before the expiration.

Usage (crontab, once a day):
    0 6 * * * cd /path/to/jebif_website && venv/bin/python manage.py expire_memberships

Reminders are sent when 30 days, then 2 days, or less remain. The date of the
last reminder is stored, so a day without run does not skip a reminder and a
reminder is never sent twice.
"""
import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse

from jebif_users.models import UserInfo
from jebif_website.utils import send_mail_safe

REMINDERS = (datetime.timedelta(days=30), datetime.timedelta(days=2))


def _send(info, text):
    return send_mail_safe(
        settings.EMAIL_SUBJECT_PREFIX + "Expiration de ton adhésion à JeBiF",
        text,
        [info.email],
    )


class Command(BaseCommand):
    help = "Expire finished memberships and send reminders before expiration"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be done, change nothing")

    def handle(self, *args, dry_run=False, **options):
        today = datetime.date.today()
        profile_url = settings.HTTP_DOMAIN + reverse("profile")
        nb_expired = nb_reminded = 0

        for info in UserInfo.objects.filter(is_member=True, is_deleted=False).select_related("user"):
            if info.has_expired():
                nb_expired += 1
                if dry_run:
                    self.stdout.write(f"Would expire: {info.email}")
                    continue
                info.is_member = False
                info.save(update_fields=["is_member"])
                _send(info, f"""
Bonjour {info.firstname},

Ton adhésion à l'association JeBiF *vient de se terminer*.
Tu peux la renouveler pour un an, gratuitement, en te rendant sur ton profil
({profile_url}) avec ton identifiant '{info.user.username}'.

En espérant te revoir très bientôt,
L'équipe du RSG-France (JeBiF)
""")
                continue

            # Most urgent reminder due today that was not sent yet
            due = [info.end_membership - delta for delta in REMINDERS if today >= info.end_membership - delta]
            if not due:
                continue
            reminder_date = max(due)
            if info.last_reminder is not None and info.last_reminder >= reminder_date:
                continue
            nb_reminded += 1
            if dry_run:
                self.stdout.write(f"Would remind: {info.email} (expires {info.end_membership})")
                continue
            if _send(info, f"""
Bonjour {info.firstname},

Ton adhésion à l'association JeBiF se termine le {info.end_membership.strftime("%d/%m/%Y")}.
Tu peux la renouveler pour un an, gratuitement, en te rendant sur ton profil
({profile_url}) avec ton identifiant '{info.user.username}'.

À bientôt,
L'équipe du RSG-France (JeBiF)
"""):
                info.last_reminder = today
                info.save(update_fields=["last_reminder"])

        self.stdout.write(f"Processed: {nb_expired} expired, {nb_reminded} reminded")
