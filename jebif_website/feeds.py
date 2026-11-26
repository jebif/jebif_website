from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator

from jebif_website.models import Article


class LatestArticlesFeed(Feed):
    """RSS feed of the latest articles (replaces the feeds of the old WordPress site)."""
    title = "JeBiF - Articles"
    description = "Les derniers articles de l'association JeBiF (RSG-France)"

    def link(self):
        return reverse("home")

    def items(self):
        return Article.objects.filter(is_draft=False).order_by("-date")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return Truncator(strip_tags(item.content)).words(80)

    def item_link(self, item):
        return reverse("article", kwargs={"slug": item.slug})

    def item_pubdate(self, item):
        return item.date

    def item_updateddate(self, item):
        return item.updated_at
