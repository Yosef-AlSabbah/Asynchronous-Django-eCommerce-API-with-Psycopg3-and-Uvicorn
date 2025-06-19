from adrf import mixins
from adrf.viewsets import ModelViewSet, GenericViewSet
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from shop.filters import ProductFilter, ProductSearchFilterBackend
from shop.models import Product, ProductStatus
from shop.permissions import IsStaff, IsOwnerOrStaff
from shop.serializers import ProductSerializer, ProductStatusSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List all approved products",
        description="Get a list of all products that have been approved.",
        tags=["Products"]
    ),
    retrieve=extend_schema(
        summary="Retrieve a product",
        description="Get detailed information about a specific product.",
        tags=["Products"]
    ),
    create=extend_schema(
        summary="Create a new product",
        description="Create a new product. The owner will be set to the currently logged-in user.",
        tags=["Products"]
    ),
    update=extend_schema(
        summary="Update a product",
        description="Update a product. Only the owner or a staff member can perform this action.",
        tags=["Products"]
    ),
    partial_update=extend_schema(
        summary="Partially update a product",
        description="Partially update a product. Only the owner or a staff member can perform this action.",
        tags=["Products"]
    ),
    destroy=extend_schema(
        summary="Delete a product",
        description="Delete a product. Only the owner or a staff member can perform this action.",
        tags=["Products"]
    ),
    mine=extend_schema(
        summary="List my products",
        description="Get a list of all products owned by the currently logged-in user.",
        tags=["Products"]
    ),
)
class AsyncProductViewSet(ModelViewSet):
    """
    Async viewset for managing products.
    """
    queryset = (
        Product.objects
        .select_related("category", "owner")
        .prefetch_related("tags")
    )
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        ProductSearchFilterBackend,
    ]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        Dynamically filter the queryset based on the action.
        For 'mine' action, it returns all products for the logged-in user.
        For other actions, it returns only approved products.

        It also optimizes database queries by using `select_related` for
        'category' and 'owner', and `prefetch_related` for 'tags'.

        Returns:
            A queryset of Product instances.
        """
        qs = super().get_queryset()
        if self.action == "mine":
            return qs.filter(owner=self.request.user)
        return qs.filter(is_approved=True)

    def get_permissions(self):
        """
        Get the permissions for the viewset.
        Made synchronous to be compatible with drf-spectacular schema generation.
        """
        if self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = self.permission_classes + [IsOwnerOrStaff]

        return [permission() for permission in self.permission_classes]

    @cache_page(settings.GENERIC_CACHE_TIMEOUT)
    @vary_on_headers("Authorization")
    async def alist(self, request, *args, **kwargs):
        return await super().alist(request, *args, **kwargs)

    @cache_page(settings.GENERIC_CACHE_TIMEOUT)
    async def aretrieve(self, request, *args, **kwargs):
        return await super().aretrieve(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
    )
    @method_decorator(cache_page(settings.GENERIC_CACHE_TIMEOUT))
    @method_decorator(vary_on_headers("Authorization"))
    async def mine(self, request, *args, **kwargs):
        """
        Gets the products for the currently logged-in user.
        """
        return await super().alist(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        summary="List Product Statuses",
        description="Retrieves a list of product statuses, available only to staff members.",
        tags=["Product Status"]
    ),
    create=extend_schema(
        summary="Create Product Status",
        description="Creates a new product status, typically for approving or rejecting a product. Available only to staff members.",
        tags=["Product Status"]
    ),
)
class AsyncProductStatusViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    """
    Async ViewSet for managing product status records.

    Provides list, create, and retrieve operations for product statuses.
    All endpoints require authenticated staff users.

    Statuses are ordered by creation date (newest first).
    """
    queryset = ProductStatus.objects.all()
    serializer_class = ProductStatusSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    ordering = ["-created_at"]
