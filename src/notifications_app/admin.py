from django.contrib import admin
from .models import WebPushSubscription


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "endpoint", "actif", "created_at", "updated_at")
    list_filter = ("actif", "created_at")
    search_fields = ("user__username", "user__email", "endpoint")
    readonly_fields = ("created_at", "updated_at")
