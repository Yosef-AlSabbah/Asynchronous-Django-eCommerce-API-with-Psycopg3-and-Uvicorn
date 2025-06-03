from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError as DjangoValidationError
from jsonschema import ValidationError

from accounts.utils import normalize_and_validate_phone

User = get_user_model()


class UsernameOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Try to authenticate with username as a phone number
        try:
            phone = normalize_and_validate_phone(username)
            try:
                user = User.objects.get(phone=phone)
                if user.check_password(password):
                    return user
                return None
            except User.DoesNotExist:
                # Valid phone format but no user found with that phone
                return None
        except (ValidationError, DjangoValidationError):
            # Not a valid phone format, try as username
            try:
                user = User.objects.get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                pass

        return None
