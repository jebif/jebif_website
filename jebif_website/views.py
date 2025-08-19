from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from .models import Article, Category, Subcategory

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage

    
class HomeView(ListView):
    model = Article
    template_name = 'jebif_website/home.html'
    paginate_by = 2
    context_object_name = 'articles'

    # get a queryset with no category
    def get_queryset(self, **kwargs):
        return Article.objects.filter(category__isnull=True, subcategory__isnull=True).order_by('-date')
    

class SubcategoryView(ListView):
    model = Article
    template_name = 'jebif_website/subcategory.html'
    paginate = 5
    context_object_name = 'articles'

    # necessary to get info for a specific subcategory
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        context['subcategory'] = get_object_or_404(Subcategory, slug=self.kwargs['subcategory_slug'])
        return context

    # get a queryset for a specific subcategory
    def get_queryset(self, **kwargs):
        category_slug = self.kwargs['category_slug']
        subcategory_slug = self.kwargs['subcategory_slug']

        category = get_object_or_404(Category, slug=category_slug)
        subcategory = get_object_or_404(Subcategory, slug=subcategory_slug, category=category)
        return Article.objects.filter(category=category, subcategory=subcategory).order_by('-date')

    
class CategoryView(ListView):
    model = Article
    template_name = 'jebif_website/category.html'
    paginate = 5
    context_object_name = 'articles'

    # necessary to get info for a specific category
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        return context

    # get a queryset for a specific category
    def get_queryset(self, **kwargs):
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(Category, slug=category_slug)
        return Article.objects.filter(category=category, subcategory__isnull=True).order_by('-date')
    

class ArticleView(DetailView):  
    model = Article
    template_name = 'jebif_website/article.html'
    context_object_name = "article"


# To upload images in the Editor (for articles)
@csrf_exempt
def upload_image(request):
    if request.method == "POST":
        image = request.FILES["file"]
        path = default_storage.save(f"uploaded_images/{image.name}", image)
        return JsonResponse({"location": f"/media/images/{path}"})
    return JsonResponse({"error": "Invalid request"}, status=400)
