from django.http import HttpResponse, JsonResponse
from django.forms.models import model_to_dict

# HTML templates for responses
_NEW_ROW_OK_HTML = (
    """<head><meta name="RETURN" content="$$RETURN_NEW_ROW_OK" /></head>"""
)
_UPDATE_ROW_OK_HTML = (
    """<head><meta name="RETURN" content="$$RETURN_UPDATE_ROW_OK" /></head>"""
)
_DELETE_ROW_OK_HTML = """<head><meta name="RETURN" content="$$RETURN_OK" /></head>"""
_OK_HTML = """<head><meta name="RETURN" content="$$RETURN_OK" /></head>"""
_REFRESH_HTML = """<head><meta name="RETURN" content="$$RETURN_REFRESH" /></head>"""
_REFRESH_PARENT_HTML = (
    """<head><meta name="RETURN" content="$$RETURN_REFRESH_PARENT" /></head>"""
)
_RELOAD_HTML = (
    """<head><meta name="RETURN" content="$$RETURN_RELOAD" /></head><body>%s</body>"""
)
_CANCEL_HTML = """<head><meta name="RETURN" content="$$RETURN_CANCEL" /></head>"""
_ERROR_HTML = (
    """<head><meta name="RETURN" content="$$RETURN_ERROR" /></head><body>%s</body>"""
)


def _is_python_agent(request):
    """Check if the request is from a Python-based user agent."""
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    return user_agent.lower().startswith("py")


def new_row_ok(request, id, obj):
    """Handle response for a successful new row creation."""
    try:
        if _is_python_agent(request):
            return JsonResponse({"action": "new_row_ok", "obj": model_to_dict(obj)})
        return HttpResponse(_NEW_ROW_OK_HTML + "id:" + str(id))
    except Exception as e:
        return HttpResponse(_ERROR_HTML % str(e), status=500)


def update_row_ok(request, id, obj):
    """Handle response for a successful row update."""
    try:
        if _is_python_agent(request):
            return JsonResponse({"action": "update_row_ok", "obj": model_to_dict(obj)})
        return HttpResponse(_UPDATE_ROW_OK_HTML + "id:" + str(id))
    except Exception as e:
        return HttpResponse(_ERROR_HTML % str(e), status=500)


def delete_row_ok(request, id, obj):
    """Handle response for a successful row deletion."""
    try:
        if _is_python_agent(request):
            return JsonResponse({"action": "delete_row_ok", "obj": model_to_dict(obj)})
        return HttpResponse(_DELETE_ROW_OK_HTML + "id:" + str(id))
    except Exception as e:
        return HttpResponse(_ERROR_HTML % str(e), status=500)


def ok(request):
    """Handle a generic OK response."""
    return HttpResponse(_OK_HTML)


def refresh(request):
    """Handle a refresh response."""
    return HttpResponse(_REFRESH_HTML)


def refresh_parent(request):
    """Handle a refresh parent response."""
    return HttpResponse(_REFRESH_PARENT_HTML)


def reload(request, new_html):
    """Handle a reload response with new HTML content."""
    return HttpResponse(_RELOAD_HTML % new_html)


def cancel(request):
    """Handle a cancel response."""
    return HttpResponse(_CANCEL_HTML)


def error(request, error_txt):
    """Handle an error response with the provided error text."""
    return HttpResponse(_ERROR_HTML % error_txt, status=400)
