from django.urls import path, include
from rest_framework.routers import DefaultRouter


app_name = 'shop'

# Create a router and register our viewsets with it
router = DefaultRouter()
# router.register(r'categories', AsyncCategoryViewSet, basename='category')
# router.register(r'products', AsyncProductViewSet, basename='product')

# URL patterns for the shop app
# urlpatterns = [
    # Include router-generated URLs
    # path('', include(router.urls)),
    # Product image endpoints
    # path('products/<slug:product_slug>/images/',
    #      AsyncProductImageViewSet.as_view({'get': 'list', 'post': 'create'}),
    #      name='product-images-list'),
    # path('products/<slug:product_slug>/images/<int:pk>/',
    #      AsyncProductImageViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
    #      name='product-images-detail'),
    # Product approval endpoint for admins
    # path('products/<int:product_id>/approve/', approve_product, name='approve-product'),
# ]
