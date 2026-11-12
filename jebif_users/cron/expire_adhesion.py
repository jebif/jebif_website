#!/usr/bin/env python
# -*- coding: utf-8

"""
Cron job: expire memberships that have passed their end_membership date,
and send reminder mails a bit before the expiration.

Usage (from the project root, with the Django environment):
    python -c "import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','jebif_main.settings'); django.setup(); from jebif_users.cron.expire_adhesion import main; main()"
"""

import datetime

ALERT_1 = datetime.timedelta(days=30)
ALERT_2 = datetime.timedelta(days=2)

from django.conf import settings

from jebif_users.models import UserInfo


def main():
    expired = []
    expire = []

    for info in UserInfo.objects.filter(is_member=True, is_deleted=False):
        if info.has_expired():
            expired.append(info)
        elif info.expire_delta() in (ALERT_1, ALERT_2):
            expire.append(info)

    for info in expired:
        info.is_member = False
        info.save()

        msg_to = [info.email]
        msg_subj = u"Expiration de ton adhésion à JeBiF"
        msg_txt = u"""
Bonjour %(firstname)s,

Ton adhésion à l'association JeBiF *vient de se terminer*.
Tu peux la renouveller pour un an, gratuitement, en te rendant sur ton profil
avec ton identifiant '%(login)s'.

En espérant te revoir très bientôt,
L'équipe du RSG-France (JeBiF)
""" % {"firstname": info.firstname, "login": info.user.username}
        if settings.DEBUG == False:
            from django.core.mail import send_mail
            send_mail(msg_subj, msg_txt, settings.DEFAULT_FROM_EMAIL, msg_to)

    for info in expire:
        msg_to = [info.email]
        msg_subj = u"Expiration de ton adhésion à JeBiF"
        msg_txt = u"""
Bonjour %(firstname)s,

Ton adhésion à l'association JeBiF se termine le %(expire_date)s.
Tu peux la renouveller pour un an, gratuitement, en te rendant sur ton profil
avec ton identifiant '%(login)s'.

À bientôt,
L'équipe du RSG-France (JeBiF)
""" % {
            "firstname": info.firstname,
            "login": info.user.username,
            "expire_date": info.end_membership.strftime("%d/%m/%Y"),
        }
        if settings.DEBUG == False:
            from django.core.mail import send_mail
            send_mail(msg_subj, msg_txt, settings.DEFAULT_FROM_EMAIL, msg_to)

    if len(expired) + len(expire) > 0:
        print("Processed: %d expired, %d about to expire" % (len(expired), len(expire)))


if __name__ == "__main__":
    main()
