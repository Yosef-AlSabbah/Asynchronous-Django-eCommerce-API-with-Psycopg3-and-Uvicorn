from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView, TokenDestroyView,
    MeAsyncViewSet,
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'users', views.UserAsyncViewSet, basename='user')
router.register(r'web-account-links', views.WebAccountLinkAsyncViewSet, basename='web-account-link')
router.register(r'telegram-account-links', views.TelegramAccountLinkAsyncViewSet, basename='telegram-account-link')

app_name = 'accounts'

# URL patterns for the accounts app
urlpatterns = [
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ USER Authentication URLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Obtain a new JWT token
    path('token/create/', TokenObtainPairView.as_view(), name='jwt-create'),

    # Refresh an existing JWT token
    path('token/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),

    # Verify an existing JWT token
    path('token/verify/', TokenVerifyView.as_view(), name='jwt-verify'),

    # Destroy an existing JWT token
    path('token/destroy/', TokenDestroyView.as_view(), name='jwt-destroy'),

    # Me endpoint
    path('me/', MeAsyncViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name='me'),
    path('me/balance/', MeAsyncViewSet.as_view({'get': 'my_balance'}), name='me-balance'),
    path('me/account-links/', MeAsyncViewSet.as_view({'get': 'my_account_links'}), name='me-account-links'),

    # Router generated URLs
    path('', include(router.urls)),

    # Authentication URLs
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    # path('login/', views.LoginView.as_view(), name='user-login'),
]
