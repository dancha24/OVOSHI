from django.urls import path, include

from . import views_shop

urlpatterns = [
    path('', include('users.api_urls')),
    path('', include('core.settings_urls')),
    path('shop/lots/', views_shop.ShopLotListCreateView.as_view(), name='shop-lot-list'),
    path('shop/lots/<int:pk>/', views_shop.ShopLotDetailView.as_view(), name='shop-lot-detail'),
]
