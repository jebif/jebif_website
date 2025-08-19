from django.urls import path, include
from .views import HomeView, SubcategoryView, CategoryView, ArticleView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('tinymce/', include('tinymce.urls')),
    path('article/<slug:slug>/', ArticleView.as_view(), name="article"),
    path('<slug:category_slug>/<slug:subcategory_slug>/', SubcategoryView.as_view(), name='articles_per_subcategory'),
    path('<slug:category_slug>/', CategoryView.as_view(), name='articles_per_category'),
    
]
