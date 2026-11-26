"""Small helpers shared by the jebif_website and jebif_users apps."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.utils.text import slugify

logger = logging.getLogger("jebif")


def get_staff_emails():
    """E-mails of "Staff" users, computed at call time (never at import time)."""
    User = get_user_model()
    return list(
        User.objects.filter(is_staff=True, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )


def send_mail_safe(subject, message, recipient_list, reply_to=None):
    """Send an e-mail without crashing the request if the SMTP server fails.

    Returns True if the mail was sent. Failures are logged (and e-mailed to
    ADMINS in production) so the data saved before the mail is never left
    behind a 500 error page.
    """
    recipient_list = [r for r in recipient_list if r]
    if not recipient_list:
        return False
    try:
        EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
            reply_to=reply_to,
        ).send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Could not send e-mail %r to %s", subject, recipient_list)
        return False


def client_ip(request):
    """IP of the client. Behind a reverse proxy, REMOTE_ADDR is the proxy's IP:
    set TRUST_X_FORWARDED_FOR=True when the proxy sets X-Forwarded-For."""
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            # The last address is the one added by our own proxy (cannot be spoofed)
            return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def hit_rate_limit(scope, key, timeout):
    """Return True if `key` already did `scope` less than `timeout` seconds ago,
    else record this hit and return False."""
    cache_key = f"ratelimit:{scope}:{key}"
    # cache.add only sets the key if it does not exist yet (atomic on most backends)
    return not cache.add(cache_key, True, timeout=timeout)


def unique_slug(instance, value, field="slug"):
    """Slug built from `value`, made unique among the objects of the instance's model."""
    base = slugify(value).replace("-", "_") or instance.__class__.__name__.lower()
    slug = base
    i = 1
    others = instance.__class__.objects.exclude(pk=instance.pk)
    while others.filter(**{field: slug}).exists():
        slug = f"{base}_{i}"
        i += 1
    return slug
