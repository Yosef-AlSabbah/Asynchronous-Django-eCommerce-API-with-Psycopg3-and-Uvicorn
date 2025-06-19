from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from .models import Product
from .utils import search_products


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """
    Custom filter to allow filtering by a comma-separated list of character values.
    This is used for filtering tags.
    """


class ProductFilter(filters.FilterSet):
    """
    A filter set for the Product model.

    This filter set allows filtering products by the following fields:
    - `category`: The category of the product.
    - `price`: The price of the product.
    - `tags`: The tags associated with the product, using their slugs.
    """
    tags = CharInFilter(field_name='tags__slug', lookup_expr='in')

    class Meta:
        """
        Meta-options for the ProductFilter.
        """
        model = Product
        fields = ['category', 'price', 'tags']


class ProductSearchFilterBackend(BaseFilterBackend):
    """
    Custom filter to search products by name and description.
    """

    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get('search', None)
        return search_products(queryset, search)