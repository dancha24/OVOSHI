from rest_framework import serializers
from django.conf import settings

from .models import SiteSettings, ShopLot


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ('vk_public_url', 'recruiter_url')


class ShopLotSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ShopLot
        fields = (
            'id', 'title', 'image', 'image_url', 'price_points',
            'sort_order', 'is_active', 'created_at',
        )
        read_only_fields = ('id', 'image_url', 'created_at')

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        base = getattr(settings, 'BACKEND_PUBLIC_URL', '') or getattr(settings, 'FRONTEND_URL', '')
        if not base:
            return obj.image.url
        base = base.rstrip('/')
        path = obj.image.url.lstrip('/')
        return f'{base}/{path}'
