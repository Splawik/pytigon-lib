from django.contrib.auth import get_user_model
from django.http import JsonResponse
from graphene_django.views import GraphQLView
from oauth2_provider.views import ProtectedResourceView


def _authenticate_jwt(request):
    """Attempt to authenticate the request using a JWT Bearer token.

    Returns:
        User object if a valid JWT token is found, otherwise None.
    """

    try:
        from graphql_jwt.utils import get_http_authorization, get_payload
    except ImportError:
        return None

    token = get_http_authorization(request)
    if not token:
        return None

    try:
        payload = get_payload(token)
        username = payload.get("username")
        if username:
            return get_user_model().objects.filter(username=username).first()
    except Exception:
        pass

    return None


class OAuth2ProtectedResourceMixin(ProtectedResourceView):
    """Mixin that protects resources using OAuth2 or JWT authentication.

    Handles OPTIONS preflight requests by allowing them through
    and verifies the user via OAuth2 token or JWT token for all other methods.
    """

    def dispatch(self, request, *args, **kwargs):
        """Dispatch incoming requests with OAuth2 or JWT authentication.

        Returns:
            HttpResponse: The response from the downstream view, or a
            JsonResponse with an error message and appropriate status code
            (401 for authentication failure, 500 for unexpected errors).
        """
        try:
            if request.method.upper() == "OPTIONS":
                return GraphQLView.dispatch(self, request, *args, **kwargs)

            if request.user.is_authenticated:
                valid = True
                user = request.user
            else:
                valid, r = self.verify_request(request)
                user = r.user

            if not valid:
                user = _authenticate_jwt(request)
                if user:
                    request.user = user
                    valid = True

            if valid:
                request.resource_owner = user
                return GraphQLView.dispatch(self, request, *args, **kwargs)

            message = {"evr-api": {"errors": ["Authentication failure"]}}
            return JsonResponse(message, status=401)

        except Exception as e:
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
