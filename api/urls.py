from django.urls import path, include

app_name = "api"

urlpatterns = [
    # Include the API v1 URLs
    path('auth/', include('accounts.urls', namespace='accounts')),
    path('shop/', include('shop.urls', namespace='shop')),
]
