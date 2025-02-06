from django.http import HttpResponse, JsonResponse
from oauth2_provider.views import ProtectedResourceView
from oauth2_provider.views.mixins import ProtectedResourceMixin
from graphene_django.views import GraphQLView
import json


class OAuth2ProtectedResourceMixin(ProtectedResourceView):
    """
    Mixin to protect resources using OAuth2 authentication.
    Handles OPTIONS preflight requests and verifies user authentication.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Dispatch method to handle incoming requests.
        """
        try:
            # Allow preflight OPTIONS requests to pass through
            if request.method.upper() == "OPTIONS":
                return super(ProtectedResourceMixin, self).dispatch(
                    request, *args, **kwargs
                )

            # Verify if the request is valid and the user is authenticated
            if request.user.is_authenticated:
                valid = True
                user = request.user
            else:
                valid, r = self.verify_request(request)
                user = r.user

            if valid:
                request.resource_owner = user
                return super(ProtectedResourceMixin, self).dispatch(
                    request, *args, **kwargs
                )
            else:
                # Return authentication failure response
                message = {"evr-api": {"errors": ["Authentication failure"]}}
                return JsonResponse(message, status=401)

        except Exception as e:
            # Handle unexpected errors
            message = {"evr-api": {"errors": [str(e)]}}
            return JsonResponse(message, status=500)


class OAuth2ProtectedGraph(OAuth2ProtectedResourceMixin, GraphQLView):
    """
    View to protect GraphQL endpoints using OAuth2 authentication.
    """

    @classmethod
    def as_view(cls, *args, **kwargs):
        """
        Class method to create a view instance.
        """
        view = super(OAuth2ProtectedGraph, cls).as_view(*args, **kwargs)
        return view
