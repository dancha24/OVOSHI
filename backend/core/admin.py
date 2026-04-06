from django.contrib import admin
from .models import SiteSettings, ShopLot


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(ShopLot)
class ShopLotAdmin(admin.ModelAdmin):
    list_display = ('title', 'price_points', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    list_editable = ('sort_order', 'is_active')
    search_fields = ('title',)
