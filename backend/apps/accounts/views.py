from __future__ import annotations

from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import User
from apps.accounts.serializers import LoginSerializer, RegisterSerializer, UserSerializer


def _session_payload(user: User) -> dict:
    """Access/refresh token pair plus the serialized user - the shape the
    frontend expects from both login and registration."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }


class LoginView(TokenObtainPairView):
    """POST email + password, receive an access/refresh token pair and the user."""

    serializer_class = LoginSerializer


class RegisterView(generics.CreateAPIView):
    """Public self-service sign up. Returns a session so the client can log in
    the new user immediately."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_session_payload(user), status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """Blacklist the caller's refresh token so the session cannot be renewed.

    The short-lived access token remains valid until it expires (≤ 15 min); the
    session is effectively over once it can no longer be refreshed.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"refresh": "This field is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            # Already expired / invalid / blacklisted - nothing to do.
            pass
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveAPIView):
    """Return the currently authenticated user."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> User:
        return self.request.user
