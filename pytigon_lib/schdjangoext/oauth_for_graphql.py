import json

from django.http import JsonResponse
from oauth2_provider.views import ProtectedResourceView
from oauth2_provider.views.mixins import ProtectedResourceMixin
from graphene_django.views import GraphQLView


class OAuth2ProtectedResourceMixin(ProtectedResourceView):
    """Mixin that protects resources using OAuth2 authentication.

    Handles OPTIONS preflight requests by allowing them through
    and verifies the user or OAuth2 token for all other methods.
    """

    def dispatch(self, request, *args, **kwargs):
        """Dispatch incoming requests with OAuth2 authentication.

        Returns:
            HttpResponse: The response from the downstream view, or a
            JsonResponse with an error message and appropriate status code
            (401 for authentication failure, 500 for unexpected errors).
        """
        try:
            # Allow preflight OPTIONS requests to pass through
            if request.method.upper() == "OPTIONS":
                return super().dispatch(request, *args, **kwargs)

            # Verify if the request is valid and the user is authenticated
            if request.user.is_authenticated:
                valid = True
                user = request.user
            else:
                valid, r = self.verify_request(request)
                user = r.user

            if valid:
                request.resource_owner = user
                return super().dispatch(request, *args, **kwargs)

            # Return authentication failure response
            message = {"evr-api": {"errors": ["Authentication failure"]}}
            return JsonResponse(message, status=401)

        except Exception as e:
            # Handle unexpected errors
            message = {"evr-api": {"errors": [str(e)]}}
            return JsonResponse(message, status=500)


class OAuth2ProtectedGraph(OAuth2ProtectedResourceMixin, GraphQLView):
    """View that combines OAuth2 protection with GraphQL endpoint handling.

    Uses OAuth2ProtectedResourceMixin for authentication and
    GraphQLView for request processing.
    """

    @classmethod
    def as_view(cls, *args, **kwargs):
        """Create a view instance combining OAuth2 and GraphQL functionality."""
        return super().as_view(*args, **kwargs)
