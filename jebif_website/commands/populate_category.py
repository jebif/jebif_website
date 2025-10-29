from django.core.management.base import BaseCommand
from django.utils.text import slugify

from jebif_website.models import Category, Subcategory

class Command(BaseCommand):
    help = "Create the default Categories with their subcategories if they don't exist yet"

    def handle(self, *args, **options):

        default_data = {
            "L'association": ["Conseil d'Administration", "Le Concept de RSG", "Nos Projets", "Répartition des Membres", "Les Statuts", "Mentions Légales"],  
            "Evènements": ["JeBiF Worksop @JOBIM", "Ptit Déjs JeBiF", "JeBiF Pubs", "TOBI: Tables Ouvertes en BioInfo"], 
            "Bioinformatique": ["Les Formations", "Trouver un Emploi en BioInformatique", "Associations et Groupes de Rencontre Francophones"],
            "Vulgarisation": ["BioInfuse", "Ateliers de Vulgarisation", "Activités Périscolaires"],
            "Liens utiles":["La SFBI", "BioInfo-fr.net", "BioInformations", "Le GDR BIM", "La CJC"], 
            "Nous rejoindre":[],
            "Contact":[]
        }

        for cat_name, subcats in default_data.items():
            category, created = Category.objects.get_or_create(name=cat_name, slug=slugify(cat_name).replace('-', '_'))
            if created:
                self.stdout.write(f"✅ Category created : {cat_name}")
            for sub_name in subcats:
                subcat, sub_created = Subcategory.objects.get_or_create(name=sub_name, slug=slugify(sub_name).replace('-', '_'), category = category)
                if sub_created:
                    self.stdout.write(f"✅ Subcategory created : {sub_name}")

        self.stdout.write(self.style.SUCCESS("✅ Categories and Subcategories created with success !"))