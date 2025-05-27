from .signals import set_current_user


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set the current user at the beginning of the request
        set_current_user(request.user)

        response = self.get_response(request)

        # Clear the user at the end of the request
        set_current_user(None)

        return response