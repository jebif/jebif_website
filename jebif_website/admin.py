from django.contrib import admin, messages
from .models import Article, Category, Subcategory, LinkedImage, WebPlatforms, Events, Participant
from .forms import ArticleAdminForm

import jebif_website.models as website

#admin.site.register(Article)
admin.site.register(Category)
#admin.site.register(Subcategory)
admin.site.register(WebPlatforms)

@admin.register(LinkedImage)
class LinkedImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'image')

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'event')

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'rank')

class PendingEventAdmin(admin.ModelAdmin):
    model=website.Events
    list_display = ('organiser', 'title', 'pending',)
    actions = ['validate_event', 'reject_event',]

    @admin.action(description="Validate event")
    def validate_event(self, request, queryset):
        count = 0
        for pending in queryset:
            if pending.pending==True:
                pending.pending=False
                pending.active=True
                pending.save()
                count += 1
            else:
                messages.error(request, f"{pending.title} was removed from the pending events, it can't be validated.")
        messages.success(request, f"{count} Events validated.")

    @admin.action(description="Reject event")
    def reject_event(self, request, queryset):
        count = 0
        for pending in queryset:
            if pending.pending==True:
                pending.pending=False
                pending.save()
                count += 1
            else:
                messages.error(request, f"{pending.title} was already removed from the pending events, it can't be unvalidated again.")
        messages.success(request, f"{count} Event(s) was(were) marked as not pending.")

admin.site.register(Events, PendingEventAdmin)

class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm
    list_display = ('title','category', 'subcategory', 'author',)

admin.site.register(Article, ArticleAdmin)
