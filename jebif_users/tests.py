import datetime
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User, Permission
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from jebif_users.models import UserInfo, end_membership
from jebif_users.views import make_verify_token, csv_safe, _membership_end_after

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD = "Un-mot-de-passe-solide-42"


def make_user(username="alice", email="alice@example.org", verified=True, is_member=False, **info):
    user = User.objects.create_user(username, email, PASSWORD)
    defaults = dict(firstname="Alice", lastname="Martin", laboratory="Lab", city_name="Paris",
                    city_cp="75005", country="France", position="PhD")
    defaults.update(info)
    UserInfo.objects.create(user=user, email=email, verified=verified, is_member=is_member, **defaults)
    return user


INFO_POST = {
    "firstname": "Alice", "lastname": "Martin", "laboratory": "Lab", "city_cp": "75005",
    "city_name": "Paris", "country": "France", "position": "PhD", "motivation": "", "know_from": "",
}


@override_settings(CACHES=LOCMEM_CACHE)
class MembershipDatesTests(TestCase):
    def test_one_year_minus_one_day(self):
        self.assertEqual(end_membership(datetime.date(2025, 3, 10)), datetime.date(2026, 3, 9))

    def test_leap_day(self):
        # A membership starting on Feb 29th ends on Feb 28th of the next year
        self.assertEqual(end_membership(datetime.date(2024, 2, 29)), datetime.date(2025, 2, 28))

    def test_init_date_uses_given_start(self):
        info = UserInfo(email="x@example.org")
        info.init_date(datetime.date(2020, 1, 1))
        self.assertEqual(info.end_membership, datetime.date(2020, 12, 31))

    def test_old_membership_keeps_anniversary(self):
        start, end = _membership_end_after(datetime.date(2019, 6, 1), today=datetime.date(2025, 3, 1))
        self.assertEqual((start, end), (datetime.date(2024, 6, 1), datetime.date(2025, 5, 31)))

    def test_is_active_member(self):
        user = make_user(is_member=True)
        info = user.info
        self.assertTrue(info.is_active_member)
        info.end_membership = datetime.date.today() - datetime.timedelta(days=1)
        self.assertFalse(info.is_active_member)


@override_settings(CACHES=LOCMEM_CACHE)
class RenewMembershipTests(TestCase):
    def test_renew_sends_mail(self):
        # Used to crash: the recipient was a string instead of a list
        user = make_user()
        self.assertTrue(user.info.re_new_membership())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alice@example.org"])
        user.info.refresh_from_db()
        self.assertTrue(user.info.is_member)

    def test_admin_action_runs(self):
        # Module-level admin actions are called with (modeladmin, request, queryset)
        admin = User.objects.create_superuser("root", "root@example.org", PASSWORD)
        user = make_user()
        self.client.force_login(admin)
        response = self.client.post(reverse("admin:auth_user_changelist"), {
            "action": "make_member", "_selected_action": [user.pk],
        })
        self.assertEqual(response.status_code, 302)
        user.info.refresh_from_db()
        self.assertTrue(user.info.is_member)

    def test_admin_cannot_deactivate_self(self):
        admin = User.objects.create_superuser("root", "root@example.org", PASSWORD)
        self.client.force_login(admin)
        self.client.post(reverse("admin:auth_user_changelist"), {
            "action": "admin_mark_deleted", "_selected_action": [admin.pk],
        })
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)


@override_settings(CACHES=LOCMEM_CACHE)
class VerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("bob", "bob@example.org", PASSWORD)
        UserInfo.objects.create(user=self.user, email="bob@example.org", verified=False)

    def verify_url(self, adhere=False, user=None):
        return reverse("verify", kwargs={"token": make_verify_token(user or self.user, adhere)})

    def test_register_sends_link(self):
        response = self.client.post(reverse("register"), {
            "username": "carol", "email": "carol@example.org",
            "password1": PASSWORD, "password2": PASSWORD,
        })
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/users/verify/", mail.outbox[0].body)

    def test_register_email_case_insensitive(self):
        response = self.client.post(reverse("register"), {
            "username": "bob2", "email": "BOB@example.org",
            "password1": PASSWORD, "password2": PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="bob2").exists())

    def test_valid_link_verifies_and_logs_in(self):
        response = self.client.post(self.verify_url(), INFO_POST)
        self.assertRedirects(response, reverse("profile"))
        self.user.info.refresh_from_db()
        self.assertTrue(self.user.info.verified)

    def test_link_is_single_use(self):
        url = self.verify_url()
        self.client.post(url, INFO_POST)
        self.client.logout()
        response = self.client.post(url, dict(INFO_POST, firstname="Pirate"))
        self.assertRedirects(response, reverse("login"))
        self.user.info.refresh_from_db()
        self.assertEqual(self.user.info.firstname, "Alice")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_tampered_token_rejected(self):
        token = make_verify_token(self.user, False)
        response = self.client.post(reverse("verify", kwargs={"token": token[:-2] + "xx"}), INFO_POST)
        self.assertRedirects(response, reverse("home"))
        self.user.info.refresh_from_db()
        self.assertFalse(self.user.info.verified)

    def test_link_bound_to_email(self):
        url = self.verify_url()
        self.user.email = "other@example.org"
        self.user.save()
        response = self.client.post(url, INFO_POST)
        self.assertRedirects(response, reverse("home"))

    def test_resend_requires_post_and_is_rate_limited(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("resend_verify")).status_code, 405)
        self.client.post(reverse("resend_verify"))
        self.client.post(reverse("resend_verify"))
        self.assertEqual(len(mail.outbox), 1)

    def test_mail_failure_does_not_crash(self):
        with mock.patch("django.core.mail.EmailMessage.send", side_effect=OSError("SMTP down")):
            response = self.client.post(reverse("register"), {
                "username": "dave", "email": "dave@example.org",
                "password1": PASSWORD, "password2": PASSWORD,
            })
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="dave").exists())


@override_settings(CACHES=LOCMEM_CACHE)
class PasswordResetTests(TestCase):
    def test_no_account_enumeration(self):
        make_user()
        known = self.client.post(reverse("password_reset"), {"email": "alice@example.org"})
        unknown = self.client.post(reverse("password_reset"), {"email": "nobody@example.org"})
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.url, unknown.url)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(CACHES=LOCMEM_CACHE)
class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def post_profile(self, **extra):
        data = dict(INFO_POST, username="alice", email="alice@example.org")
        data.update(extra)
        return self.client.post(reverse("profile"), data)

    def test_password_change_keeps_session(self):
        new = "Encore-un-autre-mdp-99"
        response = self.post_profile(current_password=PASSWORD, new_password=new, confirm_password=new)
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(self.client.get(reverse("profile")).status_code, 200)   # still logged in
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))

    def test_weak_password_rejected(self):
        self.post_profile(current_password=PASSWORD, new_password="123", confirm_password="123")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_email_change_requires_verification(self):
        self.post_profile(email="new@example.org")
        self.user.info.refresh_from_db()
        self.assertEqual(self.user.info.email, "new@example.org")
        self.assertFalse(self.user.info.verified)
        self.assertEqual(mail.outbox[-1].to, ["new@example.org"])

    def test_email_already_used(self):
        make_user("eve", "eve@example.org")
        response = self.post_profile(email="EVE@example.org")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "alice@example.org")

    def test_request_membership_requires_verified(self):
        info = self.user.info
        info.verified = False
        info.save()
        self.client.post(reverse("request_membership"))
        info.refresh_from_db()
        self.assertFalse(info.want_member)

    def test_delete_account(self):
        self.client.post(reverse("delete_account"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_admin_email_change_syncs_userinfo(self):
        self.user.email = "changed@example.org"
        self.user.save()
        self.user.info.refresh_from_db()
        self.assertEqual(self.user.info.email, "changed@example.org")


@override_settings(CACHES=LOCMEM_CACHE)
class AdminPagesTests(TestCase):
    def test_csv_injection(self):
        self.assertEqual(csv_safe("=HYPERLINK(\"x\")"), "'=HYPERLINK(\"x\")")
        self.assertEqual(csv_safe("Paris"), "Paris")

    def test_export_requires_permission(self):
        staff = User.objects.create_user("staff", "staff@example.org", PASSWORD, is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("admin_export_csv")).status_code, 302)
        staff.user_permissions.add(Permission.objects.get(codename="change_userinfo"))
        staff = User.objects.get(pk=staff.pk)   # reset the permission cache
        self.client.force_login(staff)
        make_user(is_member=True, motivation="=cmd")
        response = self.client.get(reverse("admin_export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("'=cmd", response.content.decode("utf-8-sig"))

    def test_reject_keeps_account(self):
        admin = User.objects.create_superuser("root", "root@example.org", PASSWORD)
        user = make_user(want_member=True)
        self.client.force_login(admin)
        self.client.post(reverse("admin_subscription_reject", args=[user.info.id]))
        user.info.refresh_from_db()
        self.assertFalse(user.info.want_member)
        self.assertFalse(user.info.is_deleted)


@override_settings(CACHES=LOCMEM_CACHE)
class ExpireMembershipsCommandTests(TestCase):
    def run_command(self):
        call_command("expire_memberships", stdout=StringIO())

    def test_expires_and_reminds_once(self):
        today = datetime.date.today()
        expired = make_user("old", "old@example.org", is_member=True)
        expired.info.end_membership = today - datetime.timedelta(days=1)
        expired.info.save()
        soon = make_user("soon", "soon@example.org", is_member=True)
        # 20 days left: the 30-day reminder was missed (no run that day), it must still be sent
        soon.info.end_membership = today + datetime.timedelta(days=20)
        soon.info.save()

        self.run_command()
        expired.info.refresh_from_db()
        self.assertFalse(expired.info.is_member)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["old@example.org", "soon@example.org"])

        self.run_command()   # next day: nothing new to send
        self.assertEqual(len(mail.outbox), 2)
