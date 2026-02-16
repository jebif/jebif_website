from django.urls import path, include
from .views import HomeView, SubcategoryView, CategoryView, ArticleView, get_event_view, propose_event_view, event_register_view

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('tinymce/', include('tinymce.urls')),
    path('article/<slug:slug>/', ArticleView.as_view(), name="article"),
    path("event/<int:event_id>", get_event_view, name="event"),
    path('event_form/', propose_event_view, name='event_form'),
    path('event_register/<int:event_id>/', event_register_view, name='event_register'),
    path('<slug:category_slug>/<slug:subcategory_slug>/', SubcategoryView.as_view(), name='articles_per_subcategory'),
    path('<slug:category_slug>/', CategoryView.as_view(), name='articles_per_category'),
]
