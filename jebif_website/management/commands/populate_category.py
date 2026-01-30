from django.core.management.base import BaseCommand
from django.utils.text import slugify

from jebif_website.models import Category, Subcategory

class Command(BaseCommand):
    help = "Create the default Categories with their subcategories if they don't exist yet"

    def handle(self, *args, **options):

        default_data = {
            "L'association": ["Conseil d'Administration", "Le Concept de RSG", "Nos Projets", "Répartition des Membres", "Les Statuts", "Règlement Intérieur", "Mentions Légales"],  
            "Evènements": ["JeBiF Worksop @JOBIM", "Ptit Déjs JeBiF", "JeBiF Pubs", "TOBI: Tables Ouvertes en BioInfo"], 
            "Bioinformatique": ["Les Formations", "Trouver un Emploi en BioInformatique", "Associations et Groupes de Rencontre Francophones"],
            "Vulgarisation": ["BioInfuse", "Ateliers de Vulgarisation", "Activités Périscolaires"],
            "Liens utiles":["La SFBI", "BioInfo-fr.net", "BioInformations", "Le GDR BIM", "La CJC"], 
            "Nous rejoindre":[],
            "Contact":[]
        }

        count_cat = 0
        count_sub = 0
        for cat_name, subcats in default_data.items():
            category, created = Category.objects.get_or_create(slug=slugify(cat_name).replace('-', '_'), defaults={"name": cat_name})
            if created:
                self.stdout.write(f"✅ Category created : {cat_name}")
                count_cat += 1
            for i, sub_name in enumerate(subcats):
                subcat, sub_created = Subcategory.objects.get_or_create(slug=slugify(sub_name).replace('-', '_'), category = category, rank=i, defaults={"name": sub_name})
                if sub_created:
                    self.stdout.write(f"✅ Subcategory created : {sub_name}")
                    count_sub += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {count_cat} Categories and {count_sub} Subcategories created with success !"))