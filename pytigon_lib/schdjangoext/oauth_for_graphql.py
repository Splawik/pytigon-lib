from django.http import HttpResponse
from oauth2_provider.views import ProtectedResourceView
from oauth2_provider.views.mixins import ProtectedResourceMixin
from graphene_django.views import GraphQLView
import json


class OAuth2ProtectedResourceMixin(ProtectedResourceView):
    def dispatch(self, request, *args, **kwargs):
        print(request.method, request)
        print(request.user)
        # let preflight OPTIONS requests pass
        if request.method.upper() == "OPTIONS":
            return super(ProtectedResourceMixin, self).dispatch(
                request, *args, **kwargs
            )

        # check if the request is valid and the protected resource may be accessed
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
            message = {"evr-api": {"errors": ["Authentication failure"]}}
            return HttpResponse(
                json.dumps(message, allow_nan=False),
                content_type="application/json",
                status=401,
            )


class OAuth2ProtectedGraph(OAuth2ProtectedResourceMixin, GraphQLView):
    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super(OAuth2ProtectedGraph, cls).as_view(*args, **kwargs)
        return view
