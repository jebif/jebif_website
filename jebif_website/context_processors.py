from .models import Category, LinkedImage, EventsDates, WebPlatforms, Article
from django.utils import timezone

def categories_processor(request):
    categories = Category.objects.prefetch_related('subcategory').all()
    return {'categories_nav': categories}


def images_sidebar_processor(request):
    return {
        'images_sidebar': LinkedImage.objects.all()
    }

def events_sidebar_processor(request):
    return {
        'events_sidebar': EventsDates.objects.filter(date__gte=timezone.now()).order_by('date')
    }

def platforms_sidebar_processor(request):
    return {
        'platforms_sidebar': WebPlatforms.objects.all()
    }

def recent_articles_processor(request):
    return {
        'recent_articles': Article.objects.order_by('-date')[:5]
    }