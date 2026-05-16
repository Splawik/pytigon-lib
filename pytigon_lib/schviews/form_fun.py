"""Form processing views for the schviews module.

Provides view functions that handle form rendering, validation, and
submission within the schviews framework. Includes both standalone
form views and combined list+form views.
"""

import logging
from collections.abc import Callable
from typing import Any, Dict, Optional

from django.http import HttpRequest, HttpResponse
from django.template import RequestContext

from pytigon_lib.schviews.viewtools import render_to_response, render_to_response_ext

from .perms import make_perms_url_test_fun

logger = logging.getLogger(__name__)


def form(
    request: HttpRequest,
    app_name: str,
    form_class: Any,
    template_name: str,
    object_id: Optional[int] = None,
    form_end: bool = False,
    param: Optional[Dict] = None,
    mimetype: Optional[str] = None,
) -> HttpResponse:
    """Create and process a form view.

    Handles the full lifecycle of a form: instantiation, validation,
    processing (valid/invalid/empty), and rendering the result through
    the appropriate template.

    Args:
        request: The HTTP request object.
        app_name: The name of the application.
        form_class: The form class to instantiate.
        template_name: The template to render.
        object_id: Optional object ID for form pre-population.
        form_end: Optional flag indicating form end (for multi-step forms).
        param: Optional parameters forwarded to form processing methods.
        mimetype: Optional MIME type for the response.

    Returns:
        HttpResponse: The rendered response.
    """
    try:
        form_instance = None
        if hasattr(form_class, "get_form_arguments"):
            form_args = form_class.get_form_arguments(request)
            if form_args:
                form_instance = form_class(**form_args)

        if not form_instance:
            form_instance = form_class(request.POST or None, request.FILES or None)

        if hasattr(form_instance, "preprocess_request"):
            post_data = form_instance.preprocess_request(request)
        else:
            post_data = request.POST

        if post_data:
            if hasattr(form_instance, "init"):
                form_instance.init(request)

            if form_instance.is_valid():
                result = (
                    form_instance.process(request, param)
                    if param
                    else form_instance.process(request)
                )
                if not isinstance(result, dict):
                    return result

                result.update({"form": form_instance})
                if object_id:
                    result.update({"object_id": object_id})

                if hasattr(form_instance, "render_to_response"):
                    return form_instance.render_to_response(
                        request, template_name, RequestContext(request, result)
                    )
                else:
                    doc_type = result.get("doc_type", "html")
                    return render_to_response_ext(
                        request, template_name, context=result, doc_type=doc_type
                    )
            else:
                if hasattr(form_instance, "process_invalid"):
                    result = (
                        form_instance.process_invalid(request, param)
                        if param
                        else form_instance.process_invalid(request)
                    )
                    if not isinstance(result, dict):
                        return result
                    result.update({"form": form_instance})
                    if object_id:
                        result.update({"object_id": object_id})
                    return render_to_response(
                        template_name, context=result, request=request
                    )
                else:
                    return render_to_response(
                        template_name,
                        context={"form": form_instance},
                        request=request,
                    )
        else:
            if hasattr(form_instance, "init"):
                form_instance.init(request)
            if object_id:
                form_instance.object_id = object_id

            if hasattr(form_instance, "process_empty"):
                result = (
                    form_instance.process_empty(request, param)
                    if param
                    else form_instance.process_empty(request)
                )
                if not isinstance(result, dict):
                    return result
                result["form"] = form_instance
            else:
                result = {"form": form_instance}
                if object_id:
                    result.update({"object_id": object_id})
                if param:
                    result.update(param)

            return render_to_response(template_name, context=result, request=request)
    except Exception:
        logger.exception("Error processing form '%s'", template_name)
        return HttpResponse("An error occurred while processing the form.", status=500)


def form_with_perms(app: str) -> Callable:
    """Create a form view wrapped with permission checks.

    Args:
        app: The application name used to build permission checks.

    Returns:
        A view function that checks permissions before calling ``form()``.
    """
    return make_perms_url_test_fun(app, form)


def list_and_form(
    request: HttpRequest,
    queryset: Any,
    form_class: Any,
    template_name: str,
    table_always: bool = True,
    paginate_by: Optional[int] = None,
    page: Optional[int] = None,
    allow_empty: bool = True,
    extra_context: Optional[Dict] = None,
    context_processors: Optional[Any] = None,
    template_object_name: str = "obj",
    mimetype: Optional[str] = None,
    param: Optional[Dict] = None,
) -> HttpResponse:
    """Display a list of objects alongside a form for filtering/processing.

    If POST data is present and the form is valid, the form's ``process``
    method is called to filter or modify the queryset. Otherwise, if
    ``table_always`` is True, ``process_empty`` is called on GET requests.

    Args:
        request: The HTTP request object.
        queryset: The base queryset to display and filter.
        form_class: The form class to instantiate (used for filtering).
        template_name: The template to render.
        table_always: If True, always include the table in the context.
        paginate_by: Number of items per page (reserved for future use).
        page: The current page number (reserved for future use).
        allow_empty: Whether to allow empty querysets.
        extra_context: Additional context data to merge.
        context_processors: Context processors to apply.
        template_object_name: The name of the object in the template context.
        mimetype: Optional MIME type for the response.
        param: Optional parameters forwarded to form processing methods.

    Returns:
        HttpResponse: The rendered response.
    """
    try:
        form_instance = form_class(request.POST or None)
        if request.POST and form_instance.is_valid():
            queryset = (
                form_instance.process(request, queryset, param)
                if param
                else form_instance.process(request, queryset)
            )
            extra_context = extra_context or {}
            extra_context.update({"form": form_instance})
        elif table_always:
            extra_context = extra_context or {}
            extra_context.update({"form": form_instance})
            if hasattr(form_instance, "process_empty"):
                queryset = (
                    form_instance.process_empty(request, queryset, param)
                    if param
                    else form_instance.process_empty(request, queryset)
                )

        return render_to_response(
            template_name,
            context={
                "form": form_instance,
                "object_list": queryset,
                **(extra_context or {}),
            },
            request=request,
        )
    except Exception:
        logger.exception("Error processing list_and_form '%s'", template_name)
        return HttpResponse(
            "An error occurred while processing the combined list and form.",
            status=500,
        )


def direct_to_template(
    request: HttpRequest,
    template: str,
    extra_context: Optional[Dict] = None,
    mimetype: Optional[str] = None,
    **kwargs: Any,
) -> HttpResponse:
    """Render a template directly with optional extra context.

    Useful for simple views that only need to inject URL parameters
    into a template without any model/form processing.

    Args:
        request: The HTTP request object.
        template: The template name to render.
        extra_context: Additional context data (values or callables).
        mimetype: Optional MIME type for the response.
        **kwargs: Additional URL parameters added to template context.

    Returns:
        HttpResponse: The rendered response.
    """
    try:
        context = {"params": kwargs}
        if extra_context:
            context.update(
                {k: v() if callable(v) else v for k, v in extra_context.items()}
            )
        return render_to_response(template, context=context, request=request)
    except Exception:
        logger.exception("Error rendering template '%s'", template)
        return HttpResponse(
            "An error occurred while rendering the template.", status=500
        )
