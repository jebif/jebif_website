from django.core.management.base import BaseCommand
from django.utils.text import slugify

from jebif_website.models import LinkedImage, WebPlatforms

class Command(BaseCommand):
    help = "Create the default sidebar information"

    def handle(self, *args, **options):
        self.create_platforms()
        self.create_links()

    def create_platforms(self):
        default_platforms = [
            ["BlueSky", "RSG France - JeBiF", "https://bsky.app/profile/jebif.bsky.social"],
            ["LinkedIn", "JeBiF_RSG_France", "http://www.linkedin.com/groups?gid=1806906"],
            ["Discord", "RSG France - JeBiF", "https://discord.gg/4eeptXAkcN"]
        ]

        for platform in default_platforms:
            plat, created = WebPlatforms.objects.get_or_create(title=platform[0], identification= platform[1], url = platform[2])
            if created:
                self.stdout.write(f"✅ Platform added : {plat}")
            else:
                self.stderr.write(f"Failed to add platform {plat}")
    
    def create_links(self):
        default_links = [
            ["ISCB", "images/linked_images/iscb_logo.jpg","http://www.iscb.org/"],
            ["ISCB-SC", "images/linked_images/iscb_student_logo.png","http://www.iscbsc.org/"],
            ["GDR BIMMM", "images/linked_images/gdrbim.jpg","http://www.gdr-bim.cnrs.fr/"],
            ["SFBI", "images/linked_images/SFBI_logo_without_text.png","http://www.sfbi.fr/"],
            ["Bioinfo-fr", "images/linked_images/bioinfo-fr.png","http://bioinfo-fr.net/"]
            ["Bioinformations", "images/linked_images/bioinformations.png","http://www.bioinformations.fr/"]
        ]

        for link in default_links:
            link, created = LinkedImage.objects.get_or_create(title=  link[0], image = link[1], url = link[2])
            if created:
                self.stdout.write(f"✅ Link to partner added : {link}")
            else:
                self.stderr.write(f"Failed to add partner {link}")