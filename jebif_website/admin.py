from django.contrib import admin
from .models import Article, Category, Subcategory, LinkedImage, WebPlatforms

admin.site.register(Article)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(WebPlatforms)


@admin.register(LinkedImage)
class LinkedImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'image')