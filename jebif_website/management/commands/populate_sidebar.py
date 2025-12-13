from django.core.management.base import BaseCommand
from django.utils.text import slugify

from jebif_website.models import LinkedImage, WebPlatforms

class Command(BaseCommand):
    help = "Create the default sidebar information"

    def handle(self, *args, **options):
        default_platforms = [
            ["BlueSky", "JeBif", "url"],
            ["LinkedIn", "JeBiF_RSG_France", "http://www.linkedin.com/groups?gid=1806906"],
            ["Discord", "RSG France - JeBiF", "https://discord.gg/4eeptXAkcN"]
        ]

        for platform in default_platforms:
            plat, created = WebPlatforms.objects.get_or_create(defaults={"title": platform[0], "identification": platform[1], "url": platform[2]})
            if created:
                self.stdout.write(f"✅ Platform added : {plat}")
            else:
                self.stderr.write(f"Failed to add platform {plat}")