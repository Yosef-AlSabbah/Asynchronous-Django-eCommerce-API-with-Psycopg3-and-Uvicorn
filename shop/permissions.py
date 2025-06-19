from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Custom permission to only allow owners of an object or staff to edit it.
    """
    message = 'You must be the owner of this product or a staff member to edit or delete it.'

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is the owner of the object or a staff member.
        """
        # Write permissions are only allowed to the owner of the product or staff user.
        return obj.owner == request.user


class IsStaff(BasePermission):
    """
    Custom permission to only allow staff members to perform actions.
    """
    message = 'You must be a staff member to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is a staff member.
        """
        return request.user.is_staff


class IsOwnerOrStaff(BasePermission):
    """
    Custom permission to allow either owners of an object or staff members to perform actions.
    """
    message = 'You must be the owner of this object or a staff member to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is the owner of the object or a staff member.
        """
        # Permission is granted if the user is either the owner of the object or a staff user
        return obj.owner == request.user or request.user.is_staff
