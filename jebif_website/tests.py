import datetime
import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from jebif_users.models import UserInfo
from jebif_website.models import Article, Category, Events, Participant
from jebif_website.templatetags.html_tags import sanitize_html

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD = "Un-mot-de-passe-solide-42"


def make_event(**kwargs):
    organiser = kwargs.pop("organiser", None) or User.objects.create_user("orga", "orga@example.org", PASSWORD)
    defaults = dict(title="Pub", date=timezone.now() + datetime.timedelta(days=7), localisation="Paris",
                    description="Description", organiser=organiser, pending=False, active=True)
    defaults.update(kwargs)
    return Events.objects.create(**defaults)


PARTICIPANT_POST = {"first_name": "Jean", "last_name": "Dupont", "email": "jean@example.org", "know_from": "", "k_f_text": ""}


@override_settings(CACHES=LOCMEM_CACHE)
class SanitizeTests(TestCase):
    def test_removes_scripts_keeps_formatting(self):
        html = sanitize_html('<p style="text-align:center"><strong>ok</strong><script>alert(1)</script>'
                             '<img src="/media/a.png" onerror="alert(1)"><a href="javascript:alert(1)">x</a></p>')
        self.assertIn("<strong>ok</strong>", html)
        self.assertIn('style="text-align:center"', html)
        self.assertNotIn("script", html)
        self.assertNotIn("onerror", html)
        self.assertNotIn("javascript:", html)

    def test_iframe_hosts(self):
        self.assertIn("youtube", sanitize_html('<iframe src="https://www.youtube.com/embed/x"></iframe>'))
        self.assertNotIn("evil", sanitize_html('<iframe src="https://evil.example/x"></iframe>'))


@override_settings(CACHES=LOCMEM_CACHE)
class ArticlePagesTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user("writer", "w@example.org", PASSWORD, is_staff=True)
        self.category = Category.objects.create(name="Evènements")
        for i in range(7):
            Article.objects.create(title=f"Article {i}", content="<p>texte</p><script>x()</script>",
                                   author=self.author, category=self.category)

    def test_category_is_paginated(self):
        response = self.client.get(reverse("articles_per_category", args=[self.category.slug]))
        self.assertContains(response, "Page 1 sur 2")
        self.assertNotContains(response, "<script>x()")
        response = self.client.get(reverse("articles_per_category", args=[self.category.slug]) + "?page=2")
        self.assertEqual(response.status_code, 200)

    def test_deleting_author_keeps_articles(self):
        self.author.delete()
        self.assertEqual(Article.objects.count(), 7)

    def test_feed(self):
        response = self.client.get(reverse("articles_feed"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Article 6")

    def test_home(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)


@override_settings(CACHES=LOCMEM_CACHE)
class EventTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_rejected_and_pending_events_hidden(self):
        rejected = make_event(pending=False, active=False)
        pending = make_event(organiser=rejected.organiser, pending=True, active=False)
        for event in (rejected, pending):
            self.assertEqual(self.client.get(reverse("event", args=[event.id])).status_code, 404)
            self.assertEqual(self.client.post(reverse("event_register", args=[event.id]), PARTICIPANT_POST).status_code, 404)
        self.assertEqual(Participant.objects.count(), 0)

    def test_staff_can_preview(self):
        event = make_event(pending=True, active=False)
        staff = User.objects.create_user("staff", "s@example.org", PASSWORD, is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("event", args=[event.id])).status_code, 200)

    def test_register_and_duplicates(self):
        event = make_event()
        self.client.post(reverse("event_register", args=[event.id]), PARTICIPANT_POST)
        cache.clear()
        self.client.post(reverse("event_register", args=[event.id]), dict(PARTICIPANT_POST, email="JEAN@example.org"))
        self.assertEqual(Participant.objects.count(), 1)
        self.assertFalse(Participant.objects.get().image_use)   # photo consent is opt-in

    def test_capacity(self):
        event = make_event(max_participants=1)
        self.client.post(reverse("event_register", args=[event.id]), PARTICIPANT_POST)
        cache.clear()
        self.client.post(reverse("event_register", args=[event.id]), dict(PARTICIPANT_POST, email="b@example.org"))
        self.assertEqual(Participant.objects.count(), 1)

    def test_past_event_closed(self):
        event = make_event(date=timezone.now() - datetime.timedelta(days=1))
        self.client.post(reverse("event_register", args=[event.id]), PARTICIPANT_POST)
        self.assertEqual(Participant.objects.count(), 0)

    def test_honeypot(self):
        event = make_event()
        self.client.post(reverse("event_register", args=[event.id]), dict(PARTICIPANT_POST, website_pot="spam"))
        self.assertEqual(Participant.objects.count(), 0)

    def test_deleting_organiser_keeps_event(self):
        event = make_event()
        event.organiser.delete()
        self.assertTrue(Events.objects.filter(pk=event.pk).exists())

    def test_propose_event_by_member(self):
        member = User.objects.create_user("m", "m@example.org", PASSWORD)
        UserInfo.objects.create(user=member, email="m@example.org", verified=True, is_member=True)
        User.objects.create_user("staff", "staff@example.org", PASSWORD, is_staff=True)
        self.client.force_login(member)
        date = (timezone.localtime() + datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(reverse("event_form"), {
            "title": "Atelier", "date": date, "localisation": "Lyon",
            "description": "desc", "max_participants": -1,
        })
        self.assertRedirects(response, reverse("home"))
        event = Events.objects.get(title="Atelier")
        self.assertTrue(event.pending)
        self.assertEqual(mail.outbox[0].to, ["staff@example.org"])


@override_settings(CACHES=LOCMEM_CACHE, CONTACT_EMAIL="contact@example.org")
class ContactTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_sent_to_contact_address(self):
        self.client.post(reverse("contact_form"), {"name": "Jean", "email": "jean@example.org", "commentary": "Bonjour"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["contact@example.org"])
        self.assertEqual(mail.outbox[0].reply_to, ["jean@example.org"])

    def test_rate_limit(self):
        data = {"name": "Jean", "email": "jean@example.org", "commentary": "Bonjour"}
        self.client.post(reverse("contact_form"), data)
        self.client.post(reverse("contact_form"), data)
        self.assertEqual(len(mail.outbox), 1)

    def test_newline_in_name(self):
        response = self.client.post(reverse("contact_form"), {"name": "a\nBcc: x@y.z", "email": "j@example.org", "commentary": "x"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(CACHES=LOCMEM_CACHE)
class UploadImageTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media)
        self.url = reverse("upload_image")

    def png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2)).save(buffer, "PNG")
        return SimpleUploadedFile("../../evil name.png", buffer.getvalue(), content_type="image/png")

    def test_staff_only(self):
        user = User.objects.create_user("u", "u@example.org", PASSWORD)
        self.client.force_login(user)
        response = self.client.post(self.url, {"file": self.png()}, HTTP_ORIGIN="http://testserver")
        self.assertEqual(response.status_code, 403)

    def test_upload(self):
        staff = User.objects.create_user("s", "s@example.org", PASSWORD, is_staff=True)
        self.client.force_login(staff)
        with self.settings(MEDIA_ROOT=self.media):
            response = self.client.post(self.url, {"file": self.png()}, HTTP_ORIGIN="http://testserver")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("evil", response.json()["location"])
            # Other origin refused, fake image refused
            self.assertEqual(self.client.post(self.url, {"file": self.png()}, HTTP_ORIGIN="https://evil.example").status_code, 403)
            fake = SimpleUploadedFile("x.png", b"<svg onload=alert(1)>", content_type="image/png")
            self.assertEqual(self.client.post(self.url, {"file": fake}, HTTP_ORIGIN="http://testserver").status_code, 400)


@override_settings(CACHES=LOCMEM_CACHE)
class MergedMainFeaturesTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", "s@example.org", PASSWORD, is_staff=True)
        self.category = Category.objects.create(name="Asso")

    def test_drafts_hidden_but_pagination_intact(self):
        for i in range(5):
            Article.objects.create(title=f"Public {i}", content="x", author=self.staff, category=self.category)
        draft = Article.objects.create(title="Brouillon", content="x", author=self.staff,
                                       category=self.category, is_draft=True)
        response = self.client.get(reverse("articles_per_category", args=[self.category.slug]))
        self.assertNotContains(response, "Brouillon")
        self.assertNotContains(response, "Page 1 sur 2")    # the draft does not create an empty page
        self.assertEqual(self.client.get(reverse("article", args=[draft.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("articles_feed")), "Brouillon")
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("article", args=[draft.slug])), "Brouillon")

    def test_calendar_creation_endpoints(self):
        from jebif_website.models import Meetings
        url = reverse("create_meetings")
        payload = '{"title": "CA", "date": "2030-01-03", "kind": "CA", "description": "d"}'
        user = User.objects.create_user("u", "u@example.org", PASSWORD)
        self.client.force_login(user)
        self.assertEqual(self.client.post(url, payload, content_type="application/json").status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Meetings.objects.get().color, "red")
        self.assertEqual(self.client.post(url, "not json", content_type="application/json").status_code, 400)
        response = self.client.post(reverse("create_events"), '{"title": "Pub", "date": "2030-01-04", '
                                    '"localisation": "Paris", "description": "d", "max_participants": "-1"}',
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(Events.objects.get(title="Pub").is_public)

    def test_event_page_has_qr_code(self):
        event = make_event()
        self.assertContains(self.client.get(reverse("event", args=[event.id])), "QR code")
