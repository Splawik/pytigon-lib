"""
Action response helpers for the schviews module.

Provides functions that generate standardized HTTP responses for
common CRUD operations (new row, update, delete) and utility
responses (OK, refresh, reload, cancel, error).

Each function accepts a Django HttpRequest and returns an
appropriate HttpResponse with meta tags for client-side handling.
"""

import html
import logging
from typing import Any

from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# HTML response templates
# --------------------------------------------------------------------------
# These use meta tags to communicate results back to the client
# (e.g. JavaScript frontends) in a structured way.

_NEW_ROW_OK_HTML = '<head><meta name="RETURN" content="$$RETURN_NEW_ROW_OK" /></head>'
_UPDATE_ROW_OK_HTML = (
    '<head><meta name="RETURN" content="$$RETURN_UPDATE_ROW_OK" /></head>'
)
_DELETE_ROW_OK_HTML = '<head><meta name="RETURN" content="$$RETURN_OK" /></head>'
_OK_HTML = '<head><meta name="RETURN" content="$$RETURN_OK" /></head>'
_REFRESH_HTML = '<head><meta name="RETURN" content="$$RETURN_REFRESH" /></head>'
_REFRESH_PARENT_HTML = (
    '<head><meta name="RETURN" content="$$RETURN_REFRESH_PARENT" /></head>'
)
_RELOAD_HTML_TEMPLATE = (
    '<head><meta name="RETURN" content="$$RETURN_RELOAD" /></head><body>{body}</body>'
)
_CANCEL_HTML = '<head><meta name="RETURN" content="$$RETURN_CANCEL" /></head>'
_ERROR_HTML_TEMPLATE = (
    '<head><meta name="RETURN" content="$$RETURN_ERROR" /></head><body>{body}</body>'
)


def _is_python_agent(request: HttpRequest) -> bool:
    """Check if the request originates from a Python-based user agent.

    Args:
        request: The incoming HTTP request.

    Returns:
        True if the User-Agent header starts with 'py' (case-insensitive).
    """
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    return user_agent.lower().startswith("py")


def _build_row_response(
    request: HttpRequest,
    obj_id: int,
    obj: Any,
    action_name: str,
    html_template: str,
) -> HttpResponse:
    """Build a response for a row-level operation (new/update/delete).

    For Python-based user agents the object is serialized as JSON.
    For regular (browser) clients an HTML meta-tag response is returned.

    Args:
        request: The incoming HTTP request.
        obj_id: The database ID of the affected object.
        obj: The Django model instance.
        action_name: The action key used in JSON responses.
        html_template: The HTML meta-tag template for non-Python agents.

    Returns:
        An HttpResponse with either JSON (for Python agents) or HTML.
    """
    try:
        if _is_python_agent(request):
            try:
                obj_dict = model_to_dict(obj)
            except Exception:
                logger.debug(
                    "model_to_dict failed for %s id=%s, falling back to id-only dict.",
                    action_name,
                    obj_id,
                    exc_info=True,
                )
                obj_dict = {"id": obj_id}
            return JsonResponse({"action": action_name, "obj": obj_dict})
        return HttpResponse(html_template + "id:" + html.escape(str(obj_id)))
    except Exception:
        logger.exception("Error building %s response for id=%s", action_name, obj_id)
        return HttpResponse(
            _ERROR_HTML_TEMPLATE.format(body="Internal server error"),
            status=500,
        )


def new_row_ok(request: HttpRequest, id: int, obj: Any) -> HttpResponse:
    """Return a response indicating a new row was successfully created.

    Args:
        request: The incoming HTTP request.
        id: The database ID of the newly created row.
        obj: The Django model instance that was created.

    Returns:
        HttpResponse with meta tag ``$$RETURN_NEW_ROW_OK`` and the row id.
    """
    return _build_row_response(request, id, obj, "new_row_ok", _NEW_ROW_OK_HTML)


def update_row_ok(request: HttpRequest, id: int, obj: Any) -> HttpResponse:
    """Return a response indicating a row was successfully updated.

    Args:
        request: The incoming HTTP request.
        id: The database ID of the updated row.
        obj: The Django model instance that was updated.

    Returns:
        HttpResponse with meta tag ``$$RETURN_UPDATE_ROW_OK`` and the row id.
    """
    return _build_row_response(request, id, obj, "update_row_ok", _UPDATE_ROW_OK_HTML)


def delete_row_ok(request: HttpRequest, id: int, obj: Any) -> HttpResponse:
    """Return a response indicating a row was successfully deleted.

    Args:
        request: The incoming HTTP request.
        id: The database ID of the deleted row.
        obj: The Django model instance that was deleted.

    Returns:
        HttpResponse with meta tag ``$$RETURN_OK`` and the row id.
    """
    return _build_row_response(request, id, obj, "delete_row_ok", _DELETE_ROW_OK_HTML)


def ok(request: HttpRequest) -> HttpResponse:
    """Return a generic OK response.

    Args:
        request: The incoming HTTP request.

    Returns:
        HttpResponse with meta tag ``$$RETURN_OK``.
    """
    return HttpResponse(_OK_HTML)


def refresh(request: HttpRequest) -> HttpResponse:
    """Return a response that triggers a client-side page refresh.

    Args:
        request: The incoming HTTP request.

    Returns:
        HttpResponse with meta tag ``$$RETURN_REFRESH``.
    """
    return HttpResponse(_REFRESH_HTML)


def refresh_parent(request: HttpRequest) -> HttpResponse:
    """Return a response that triggers a refresh of the parent frame/window.

    Args:
        request: The incoming HTTP request.

    Returns:
        HttpResponse with meta tag ``$$RETURN_REFRESH_PARENT``.
    """
    return HttpResponse(_REFRESH_PARENT_HTML)


def reload(request: HttpRequest, new_html: str) -> HttpResponse:
    """Return a response that instructs the client to reload with new content.

    Args:
        request: The incoming HTTP request.
        new_html: The new HTML body to embed in the response.

    Returns:
        HttpResponse with meta tag ``$$RETURN_RELOAD`` and the provided HTML.
    """
    return HttpResponse(_RELOAD_HTML_TEMPLATE.format(body=new_html))


def cancel(request: HttpRequest) -> HttpResponse:
    """Return a response that triggers a client-side cancel action.

    Args:
        request: The incoming HTTP request.

    Returns:
        HttpResponse with meta tag ``$$RETURN_CANCEL``.
    """
    return HttpResponse(_CANCEL_HTML)


def error(request: HttpRequest, error_txt: str) -> HttpResponse:
    """Return an error response with the provided error text.

    The error message is HTML-escaped to prevent XSS if the text
    originates from user input.  The response uses HTTP status 400.

    Args:
        request: The incoming HTTP request.
        error_txt: The error message to embed in the response body.

    Returns:
        HttpResponse with meta tag ``$$RETURN_ERROR``, status 400.
    """
    return HttpResponse(
        _ERROR_HTML_TEMPLATE.format(body=html.escape(error_txt)),
        status=400,
    )
