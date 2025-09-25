from django.contrib import admin, messages
from .models import Article, Category, Subcategory, LinkedImage, WebPlatforms, EventsDates

import jebif_website.models as website

admin.site.register(Article)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(WebPlatforms)
admin.site.register(EventsDates)


@admin.register(LinkedImage)
class LinkedImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'image')


class PendingEventAdmin(admin.ModelAdmin):
    model=website.PendingEvents
    list_display = ('user', 'title', 'pending',)
    actions = ['validate_event', 'unvalidate_event',]

    @admin.action(description="Validate event")
    def validate_event(self, request, queryset):
        count = 0
        for pending in queryset:
            if pending.pending==True:
                website.EventsDates.objects.create(title=pending.title,
                                                    date=pending.date,
                                                    localisation=pending.localisation,
                                                    )
                pending.pending=False
                pending.save()
                count += 1
            else:
                messages.error(request, f"{pending.title} was removed from the pending events, it can't be validated.")
        messages.success(request, f"{count} Events validated.")

    @admin.action(description="Unvalidate event")
    def unvalidate_event(self, request, queryset):
        count = 0
        for pending in queryset:
            if pending.pending==True:
                pending.pending=False
                pending.save()
                count += 1
            else:
                messages.error(request, f"{pending.title} was already removed from the pending events, it can't be unvalidated again.")
        messages.success(request, f"{count} Event(s) was(were) marked as not pending.")

  

admin.site.register(website.PendingEvents,PendingEventAdmin)