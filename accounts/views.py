import logging
from typing import Final

from adrf.views import APIView
from adrf.viewsets import ModelViewSet, mixins, GenericViewSet
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView as BaseTokenObtainPairView,
    TokenRefreshView as BaseTokenRefreshView,
    TokenVerifyView as BaseTokenVerifyView, TokenBlacklistView,
)

from accounts.models import WebAccountLink, TelegramAccountLink
from accounts.serializers import (
    UserSerializer,
    WebAccountLinkSerializer,
    TelegramAccountLinkSerializer, RefreshTokenSerializer, UserRegistrationSerializer,
)
from dynamic_config.services import ConfigService

User = get_user_model()

logger = logging.getLogger(__name__)


class UserAsyncViewSet(ModelViewSet):
    """
    Async viewset for user management with custom access control.

    Provides CRUD operations for users with the following access control:
    - List: Only staff members
    - Retrieve: Only staff members (use /me/ for own data)
    - Update: Users can update themselves, staff can update anyone
    - Delete: Users can delete themselves, staff can delete anyone
    - Balance updates: Only admins (superusers)
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    async def get_queryset(self):
        """
        Override to return the queryset asynchronously.
        Only staff can see all users, regular users see none in list view.
        """
        return User.objects.all()

    @extend_schema(
        summary="List all users",
        description="Get a list of all users. Only accessible by staff members.",
        tags=["User Management"],
        responses={
            200: UserSerializer(many=True),
            403: OpenApiResponse(description="Only staff members can list users")
        }
    )
    async def list(self, request, *args, **kwargs):
        """
        Only staff members can list users.
        """
        if not request.user.is_staff:
            raise PermissionDenied("Only staff members can list users.")

        return await super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a user",
        description="Get details of a specific user. Only accessible by staff members. Regular users should use /users/me/ instead.",
        tags=["User Management"],
        responses={
            200: UserSerializer,
            403: OpenApiResponse(description="Only staff members can retrieve user details"),
            404: OpenApiResponse(description="User not found")
        }
    )
    async def retrieve(self, request, *args, **kwargs):
        """
        Only staff members can retrieve other users' data.
        Regular users should use the 'me' action instead.
        """
        if not request.user.is_staff:
            raise PermissionDenied("Only staff members can retrieve user details. Use /users/me/ to get your own data.")

        return await super().retrieve(request, *args, **kwargs)

    async def get_object(self):
        """
        Override to get object asynchronously.
        """
        queryset = await self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        # Use sync_to_async to handle the database query
        obj = await sync_to_async(queryset.get)(**filter_kwargs)

        # May raise a permission denied
        await sync_to_async(self.check_object_permissions)(self.request, obj)

        return obj

    @extend_schema(
        summary="Update a user",
        description="Update user data. Users can update themselves, staff can update anyone. Balance can only be updated by admins.",
        tags=["User Management"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found")
        }
    )
    async def update(self, request, *args, **kwargs):
        """
        Users can update themselves, staff can update anyone.
        Balance can only be updated by admins.
        """
        instance = await self.get_object()

        # Check if user can update this instance
        if not request.user.is_staff and instance != request.user:
            raise PermissionDenied("You can only update your own profile.")

        # Check if balance is being updated and user is not admin
        if 'balance' in request.data and not request.user.is_superuser:
            raise PermissionDenied("Only administrators can update user balance.")

        # Call parent's update method and return its result
        return await super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a user",
        description="Partially update user data. Users can update themselves, staff can update anyone. Balance can only be updated by admins.",
        tags=["User Management"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found")
        }
    )
    async def partial_update(self, request, *args, **kwargs):
        """
        Users can partially update themselves, staff can update anyone.
        Balance can only be updated by admins.
        """
        instance = await self.get_object()

        # Check if user can update this instance
        if not request.user.is_staff and instance != request.user:
            raise PermissionDenied("You can only update your own profile.")

        # Check if balance is being updated and user is not admin
        if 'balance' in request.data and not request.user.is_superuser:
            raise PermissionDenied("Only administrators can update user balance.")

        # Call parent's partial_update method and return its result
        return await super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a user",
        description="Delete a user. Users can delete themselves, staff can delete anyone.",
        tags=["User Management"],
        responses={
            204: OpenApiResponse(description="User deleted successfully"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found")
        }
    )
    async def destroy(self, request, *args, **kwargs):
        """
        Users can delete themselves, staff can delete anyone.
        """
        instance = await self.get_object()

        # Check if user can delete this instance
        if not request.user.is_staff and instance != request.user:
            raise PermissionDenied("You can only delete your own account.")

        return await super().destroy(request, *args, **kwargs)

    @extend_schema(summary="Create a new user",
                   description="This endpoint is disabled. Use dedicated registration endpoint instead.",
                   tags=["User Management"],
                   responses={403: OpenApiResponse(description="User creation through this endpoint is disabled")})
    async def create(self, request, *args, **kwargs):
        """ User creation is disabled through this endpoint. Use dedicated registration endpoint instead. """
        raise PermissionDenied(
            "User creation through this endpoint is disabled. " "Please use the dedicated registration endpoint."
        )

    async def perform_create(self, serializer):
        """
        Perform creation asynchronously.
        """
        await sync_to_async(serializer.save)()

    async def perform_update(self, serializer):
        """
        Perform update asynchronously.
        """
        await sync_to_async(serializer.save)()

    async def perform_destroy(self, instance):
        """
        Perform deletion asynchronously.
        """
        await sync_to_async(instance.delete)()

    @extend_schema(
        summary="Get user balance",
        description="Get a user's current balance. Users can only see their own balance, staff can see anyone's.",
        tags=["Payments"],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'balance': {'type': 'string', 'description': 'User balance'}
                }
            },
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found")
        }
    )
    @action(detail=True, methods=['get'])
    async def balance(self, request, pk=None):
        """
        Get user's current balance.
        Users can only see their own balance, staff can see anyone's.
        """
        user = await self.get_object()

        # Check permissions
        if not request.user.is_staff and user != request.user:
            raise PermissionDenied("You can only view your own balance.")

        return Response({'balance': str(user.balance)})

    @extend_schema(
        summary="Update user balance (Admin only)",
        description="Update a user's balance. Only administrators can perform this action.",
        tags=["Payments"],
        request={
            'type': 'object',
            'properties': {
                'balance': {'type': 'string', 'description': 'New balance value'}
            },
            'required': ['balance']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'balance': {'type': 'string', 'description': 'Updated balance'}
                }
            },
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Only administrators can update user balance"),
            404: OpenApiResponse(description="User not found")
        }
    )
    @action(detail=True, methods=['patch'])
    async def update_balance(self, request, pk=None):
        """
        Update user's balance. Only admins can do this.
        """
        if not request.user.is_superuser:
            raise PermissionDenied("Only administrators can update user balance.")

        user = await self.get_object()
        balance = request.data.get('balance')

        if balance is None:
            return Response(
                {'error': 'balance field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.balance = balance
        await sync_to_async(user.save)(update_fields=['balance'])

        return Response({'balance': str(user.balance)})

    @extend_schema(
        summary="Get user account links",
        description="Get all account links for a user. Users can only see their own links, staff can see anyone's.",
        tags=["User Management"],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'web_links': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    },
                    'telegram_links': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    }
                }
            },
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found")
        }
    )
    @action(detail=True, methods=['get'])
    async def account_links(self, request, pk=None):
        """
        Get all account links for a user.
        Users can only see their own links, staff can see anyone's.
        """
        user = await self.get_object()

        # Check permissions
        if not request.user.is_staff and user != request.user:
            raise PermissionDenied("You can only view your own account links.")

        # Get web account links
        web_links = await sync_to_async(list)(
            user.webaccountlink_links.all()
        )

        # Get telegram account links
        telegram_links = await sync_to_async(list)(
            user.telegramaccountlink_links.all()
        )

        web_serializer = WebAccountLinkSerializer(web_links, many=True)
        telegram_serializer = TelegramAccountLinkSerializer(telegram_links, many=True)

        return Response({
            'web_links': web_serializer.data,
            'telegram_links': telegram_serializer.data
        })


class MeAsyncViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    async def get_object(self):
        return self.request.user

    @extend_schema(
        summary="Get current user data",
        description="Get the authenticated user's own data.",
        tags=["User Management"],
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Authentication required")
        }
    )
    async def retrieve(self, request, *args, **kwargs):
        serializer = await sync_to_async(self.get_serializer)(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Update current user data",
        description="Update the authenticated user's own data. Balance field is automatically excluded.",
        tags=["User Management"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required")
        },
        examples=[
            OpenApiExample(
                "Sample update",
                value={
                    "first_name": "First Name",
                    "last_name": "Second Name",
                    "phone": "+972 50-000-0000"
                },
                request_only=True
            )
        ]
    )
    async def update(self, request, *args, **kwargs):
        request_data = request.data.copy()
        if 'balance' in request_data:
            request_data.pop('balance')
        serializer = self.get_serializer(
            request.user,
            data=request_data,
            partial=False
        )
        valid = await sync_to_async(serializer.is_valid)()
        if valid:
            await sync_to_async(serializer.save)()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Partially update current user data",
        description="Partially update the authenticated user's own data. Balance field is automatically excluded.",
        tags=["User Management"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    async def partial_update(self, request, *args, **kwargs):
        request_data = request.data.copy()
        if 'balance' in request_data:
            request_data.pop('balance')
        serializer = self.get_serializer(
            request.user,
            data=request_data,
            partial=True
        )
        valid = await sync_to_async(serializer.is_valid)()
        if valid:
            await sync_to_async(serializer.save)()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get current user balance",
        description="Get the authenticated user's current balance.",
        tags=["Payments"],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'balance': {'type': 'string', 'description': 'User balance'}
                }
            },
            401: OpenApiResponse(description="Authentication required")
        }
    )
    @action(detail=False, methods=['get'])
    async def my_balance(self, request):
        return Response({'balance': str(request.user.balance)})

    @extend_schema(
        summary="Get current user account links",
        description="Get the authenticated user's account links.",
        tags=["User Management"],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'web_links': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    },
                    'telegram_links': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    }
                }
            },
            401: OpenApiResponse(description="Authentication required")
        }
    )
    @action(detail=False, methods=['get'])
    async def my_account_links(self, request):
        """
        Get current user's own account links.
        """
        user = request.user

        # Get web account links
        web_links = await sync_to_async(list)(
            user.webaccountlink_links.all()
        )

        # Get telegram account links
        telegram_links = await sync_to_async(list)(
            user.telegramaccountlink_links.all()
        )

        web_serializer = WebAccountLinkSerializer(web_links, many=True)
        telegram_serializer = TelegramAccountLinkSerializer(telegram_links, many=True)

        return Response({
            'web_links': web_serializer.data,
            'telegram_links': telegram_serializer.data
        })


class WebAccountLinkAsyncViewSet(ModelViewSet):
    """
    Async viewset for web account link management.

    Provides CRUD operations for web account links.
    """
    serializer_class = WebAccountLinkSerializer
    permission_classes = [IsAuthenticated]

    async def get_queryset(self):
        """
        Return queryset filtered by current user if needed.
        Regular users only see their own links, staff can see all.
        """
        if self.request.user.is_staff:
            return WebAccountLink.objects.all()
        else:
            return WebAccountLink.objects.filter(user=self.request.user)

    async def get_object(self):
        """
        Override to get object asynchronously.
        """
        queryset = await self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        obj = await sync_to_async(queryset.get)(**filter_kwargs)
        await sync_to_async(self.check_object_permissions)(self.request, obj)

        return obj

    @extend_schema(
        summary="Create a web account link",
        description="Create a new web account link.",
        tags=["Account Linking"],
        request=WebAccountLinkSerializer,
        responses={
            201: WebAccountLinkSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    async def create(self, request, *args, **kwargs):
        return await super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List web account links",
        description="List web account links accessible to the current user.",
        tags=["Account Linking"],
        responses={
            200: WebAccountLinkSerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    async def list(self, request, *args, **kwargs):
        return await super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a web account link",
        description="Retrieve a specific web account link.",
        tags=["Account Linking"],
        responses={
            200: WebAccountLinkSerializer,
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def retrieve(self, request, *args, **kwargs):
        return await super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a web account link",
        description="Update a specific web account link.",
        tags=["Account Linking"],
        request=WebAccountLinkSerializer,
        responses={
            200: WebAccountLinkSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def update(self, request, *args, **kwargs):
        return await super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a web account link",
        description="Partially update a specific web account link.",
        tags=["Account Linking"],
        request=WebAccountLinkSerializer,
        responses={
            200: WebAccountLinkSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def partial_update(self, request, *args, **kwargs):
        return await super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a web account link",
        description="Delete a specific web account link.",
        tags=["Account Linking"],
        responses={
            204: OpenApiResponse(description="No content"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def destroy(self, request, *args, **kwargs):
        return await super().destroy(request, *args, **kwargs)

    async def perform_create(self, serializer):
        """
        Perform creation asynchronously.
        Ensure users can only create links for themselves.
        """
        # Ensure the user can only create links for themselves
        if 'user' in serializer.validated_data and serializer.validated_data['user'] != self.request.user:
            if not self.request.user.is_staff:
                raise PermissionDenied("You can only create account links for yourself.")
        await sync_to_async(serializer.save)()

    async def perform_update(self, serializer):
        """
        Perform update asynchronously.
        Ensure users can only update their own links.
        """
        instance = serializer.instance
        # Check if user is trying to update someone else's link
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only update your own account links.")
        # Prevent changing the user
        if 'user' in serializer.validated_data and serializer.validated_data['user'] != instance.user:
            if not self.request.user.is_staff:
                raise PermissionDenied("You cannot change the user of an account link.")
        await sync_to_async(serializer.save)()

    async def perform_destroy(self, instance):
        """
        Perform deletion asynchronously.
        """
        await sync_to_async(instance.delete)()

    @extend_schema(
        summary="Get web account links by user",
        description="Get web account links for a specific user.",
        tags=["Account Linking"],
        parameters=[
            OpenApiParameter(
                name='user_id',
                description="User ID to filter by",
                required=True,
                type=int,
                location='query'
            )
        ],
        responses={
            200: WebAccountLinkSerializer(many=True),
            400: OpenApiResponse(description="user_id parameter is required")
        }
    )
    @action(detail=False, methods=['get'])
    async def by_user(self, request):
        """
        Get web account links for a specific user.
        Regular users can only query their own links, staff can query any user's links.
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Permission check
        if not request.user.is_staff and str(request.user.id) != user_id:
            raise PermissionDenied("You can only view your own account links.")

        links = await sync_to_async(list)(
            WebAccountLink.objects.filter(user_id=user_id)
        )

        serializer = self.get_serializer(links, many=True)
        return Response(serializer.data)


class TelegramAccountLinkAsyncViewSet(ModelViewSet):
    """
    Async viewset for telegram account link management.

    Provides CRUD operations for telegram account links.
    """
    serializer_class = TelegramAccountLinkSerializer
    permission_classes = [IsAuthenticated]

    async def get_queryset(self):
        """
        Return queryset filtered by current user if needed.
        """
        return TelegramAccountLink.objects.all()

    async def get_object(self):
        """
        Override to get an object asynchronously.
        """
        queryset = await self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        obj = await sync_to_async(queryset.get)(**filter_kwargs)
        await sync_to_async(self.check_object_permissions)(self.request, obj)

        return obj

    @extend_schema(
        summary="Create a Telegram account link",
        description="Create a new Telegram account link.",
        tags=["Account Linking"],
        request=TelegramAccountLinkSerializer,
        responses={
            201: TelegramAccountLinkSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    async def create(self, request, *args, **kwargs):
        return await super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List Telegram account links",
        description="List all Telegram account links.",
        tags=["Account Linking"],
        responses={
            200: TelegramAccountLinkSerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    async def list(self, request, *args, **kwargs):
        return await super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a Telegram account link",
        description="Retrieve a specific Telegram account link.",
        tags=["Account Linking"],
        responses={
            200: TelegramAccountLinkSerializer,
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def retrieve(self, request, *args, **kwargs):
        return await super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a Telegram account link",
        description="Update a specific Telegram account link.",
        tags=["Account Linking"],
        request=TelegramAccountLinkSerializer,
        responses={
            200: TelegramAccountLinkSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def update(self, request, *args, **kwargs):
        return await super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a Telegram account link",
        description="Partially update a specific Telegram account link.",
        tags=["Account Linking"],
        request=TelegramAccountLinkSerializer,
        responses={
            200: TelegramAccountLinkSerializer,
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def partial_update(self, request, *args, **kwargs):
        return await super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a Telegram account link",
        description="Delete a specific Telegram account link.",
        tags=["Account Linking"],
        responses={
            204: OpenApiResponse(description="No content"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Not found")
        }
    )
    async def destroy(self, request, *args, **kwargs):
        return await super().destroy(request, *args, **kwargs)

    async def perform_create(self, serializer):
        """
        Perform creation asynchronously.
        """
        await sync_to_async(serializer.save)()

    async def perform_update(self, serializer):
        """
        Perform update asynchronously.
        """
        await sync_to_async(serializer.save)()

    async def perform_destroy(self, instance):
        """
        Perform deletion asynchronously.
        """
        await sync_to_async(instance.delete)()

    @extend_schema(
        summary="Get telegram account links by user",
        description="Get telegram account links for a specific user.",
        tags=["Account Linking"],
        parameters=[
            OpenApiParameter(
                name='user_id',
                description="User ID to filter by",
                required=True,
                type=int,
                location='query'
            )
        ],
        responses={
            200: TelegramAccountLinkSerializer(many=True),
            400: OpenApiResponse(description="user_id parameter is required")
        }
    )
    @action(detail=False, methods=['get'])
    async def by_user(self, request):
        """
        Get telegram account links for a specific user.
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        links = await sync_to_async(list)(
            TelegramAccountLink.objects.filter(user_id=user_id)
        )

        serializer = self.get_serializer(links, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get telegram account link by telegram ID",
        description="Get account link by telegram ID.",
        tags=["Account Linking"],
        parameters=[
            OpenApiParameter(
                name='telegram_id',
                description="Telegram ID to search for",
                required=True,
                type=str,
                location='query'
            )
        ],
        responses={
            200: TelegramAccountLinkSerializer,
            400: OpenApiResponse(description="telegram_id parameter is required"),
            404: OpenApiResponse(description="Account link not found")
        }
    )
    @action(detail=False, methods=['get'])
    async def by_telegram_id(self, request):
        """
        Get account link by telegram ID.
        """
        telegram_id = request.query_params.get('telegram_id')
        if not telegram_id:
            return Response(
                {'error': 'telegram_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            link = await sync_to_async(
                TelegramAccountLink.objects.get
            )(telegram_id=telegram_id)

            serializer = self.get_serializer(link)
            return Response(serializer.data)
        except TelegramAccountLink.DoesNotExist:
            return Response(
                {'error': 'Account link not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserRegistrationView(APIView):
    """
    Async view for user registration.
    Allows new users to create accounts with username, password, and phone number.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="Create a new user account with username, password, and phone number.",
        tags=["User Authentication"],
        request=UserRegistrationSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Bad request - validation error")
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return Response({
                "message": "Token successfully obtained",
                "data": response.data
            }, status=response.status_code)
        except Exception as e:
            logger.error(f"Error during token obtain: {e}", exc_info=True)
            raise


class TokenRefreshView(BaseTokenRefreshView):
    """
    Handle POST requests to refresh an access token using a refresh token.
    """

    @extend_schema(
        operation_id="token_refresh",
        description="Refresh an access token using a refresh token.",
        tags=["User Authentication"],
        responses={
            200: OpenApiResponse(description="Access token successfully refreshed."),
            400: OpenApiResponse(description="Invalid refresh token."),
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return Response({
                "message": "Access token successfully refreshed",
                "data": response.data
            }, status=response.status_code)
        except Exception as e:
            logger.error(f"Error during token refresh: {e}", exc_info=True)
            raise


class TokenVerifyView(BaseTokenVerifyView):
    """
    Verify if an access token is valid.
    """

    @extend_schema(
        operation_id="token_verify",
        description="Verify if an access token is valid.",
        tags=["User Authentication"],
        responses={
            200: OpenApiResponse(description="Token is valid."),
            401: OpenApiResponse(description="Token is invalid or expired."),
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return Response({
                "message": "Token is valid",
                "data": response.data
            }, status=response.status_code)
        except Exception as e:
            logger.error(f"Error during token verification: {e}", exc_info=True)
            raise


class TokenDestroyView(TokenBlacklistView):
    """
    Log out the user by blacklisting their refresh token.
    """
    serializer_class = RefreshTokenSerializer

    @extend_schema(
        operation_id="logout_user",
        description="Log out the user by blacklisting their refresh token.",
        tags=["User Authentication"],
        request=RefreshTokenSerializer,
        responses={
            205: OpenApiResponse(description="Successfully logged out"),
            400: OpenApiResponse(description="Invalid Token"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            refresh_token = serializer.validated_data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                "message": "Successfully logged out"
            }, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error(f"Error during logout: {e}", exc_info=True)
            raise

class TokenObtainPairView(BaseTokenObtainPairView):
    """
    Handle POST requests to obtain a new pair of access and refresh tokens.
    Limits the number of devices a user can be logged into simultaneously.
    """

    @extend_schema(
        operation_id="token_obtain",
        description="Obtain a new pair of access and refresh tokens. Limited by a configurable number of active devices per user.",
        tags=["User Authentication"],
        responses={
            200: OpenApiResponse(description="Token successfully obtained."),
            400: OpenApiResponse(description="Invalid credentials."),
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            # First validate credentials and get the token response
            response = super().post(request, *args, **kwargs)

            # Extract user from token instead of additional database query
            from rest_framework_simplejwt.tokens import AccessToken
            token_data = response.data.get('access')
            token = AccessToken(token_data)
            user_id = token.payload.get('user_id')

            # Get max devices from config (without extra query if cached)
            max_active_devices = ConfigService.get('MAX_ACTIVE_DEVICES', default=2)

            # Only check token limit if we have the user_id
            if user_id:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

                # Single efficient query to count active tokens
                active_tokens_count = OutstandingToken.objects.filter(
                    user_id=user_id,
                    blacklistedtoken__isnull=True
                ).count()

                # Prepare response data
                response_data = {
                    "message": "Token successfully obtained",
                    "data": response.data
                }

                # If the user already has too many active tokens
                if active_tokens_count > max_active_devices:
                    # Get and blacklist the oldest token in a single operation
                    oldest_token = OutstandingToken.objects.filter(
                        user_id=user_id,
                        blacklistedtoken__isnull=True
                    ).order_by('created_at').first()

                    if oldest_token:
                        RefreshToken(oldest_token.token).blacklist()
                        logger.info(f"Blacklisted oldest token for user ID {user_id} due to device limit")
                        response_data[
                            "device_limit_info"] = f"You have reached the maximum number of devices ({max_active_devices}). You have been logged out from your oldest device."

                return Response(response_data, status=response.status_code)

            # Fallback for an unexpected case where user_id is not in token
            return response

        except Exception as e:
            logger.error(f"Error during token obtain: {e}", exc_info=True)
            raise