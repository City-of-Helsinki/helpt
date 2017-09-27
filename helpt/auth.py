from rest_framework.authentication import SessionAuthentication


class HelptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        """
        Do Not Enforce CSRF validation for session based authentication.
        """
        pass
