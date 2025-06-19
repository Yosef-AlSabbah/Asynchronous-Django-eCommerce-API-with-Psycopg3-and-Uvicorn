from django.urls import path, include
from rest_framework_nested import routers  # Import nested routers

from .views import AsyncProductViewSet, AsyncProductStatusViewSet

app_name = 'shop'

# Main router
router = routers.DefaultRouter()
router.register(r'products', AsyncProductViewSet, basename='product')
router.register(r'product-statuses', AsyncProductStatusViewSet, basename='product-status')

# Nested router for product approvals
# This will create URLs like /products/{product_pk}/approvals/
products_router = routers.NestedSimpleRouter(router, r'products', lookup='product')

# URL patterns for the shop app
urlpatterns = [
    path('', include(router.urls)),
    path('', include(products_router.urls)),  # Include nested routes
]
