"""Module contains views for form processing."""

from django.http import HttpResponse
from django.template import RequestContext, loader
from django.conf import settings
from pytigon_lib.schviews.viewtools import render_to_response
from .perms import make_perms_url_test_fun
from .viewtools import render_to_response_ext


def form(
    request,
    app_name,
    form_class,
    template_name,
    object_id=None,
    form_end=False,
    param=None,
    mimetype=None,
):
    """Create and process a form view.

    Args:
        request: The HTTP request object.
        app_name: The name of the application.
        form_class: The form class to instantiate.
        template_name: The template to render.
        object_id: Optional object ID for the form.
        form_end: Optional flag indicating form end.
        param: Optional parameters for form processing.
        mimetype: Optional mimetype for the response.

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
                        form_instance.process(request, param)
                        if param
                        else form_instance.process(request)
                    )
                    result.update({"form": form_instance})
                    if object_id:
                        result.update({"object_id": object_id})
                    return render_to_response(
                        template_name, context=result, request=request
                    )
                else:
                    return render_to_response(
                        template_name, context={"form": form_instance}, request=request
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
                result["form"] = form_instance
            else:
                result = {"form": form_instance}
                if object_id:
                    result.update({"object_id": object_id})
                if param:
                    result.update(param)

            return render_to_response(template_name, context=result, request=request)
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}", status=500)


def form_with_perms(app):
    """Create a form view with permissions."""
    return make_perms_url_test_fun(app, form)


def list_and_form(
    request,
    queryset,
    form_class,
    template_name,
    table_always=True,
    paginate_by=None,
    page=None,
    allow_empty=True,
    extra_context=None,
    context_processors=None,
    template_object_name="obj",
    mimetype=None,
    param=None,
):
    """List and process a form view.

    Args:
        request: The HTTP request object.
        queryset: The queryset to display.
        form_class: The form class to instantiate.
        template_name: The template to render.
        table_always: Whether to always display the table.
        paginate_by: Number of items per page.
        page: The current page number.
        allow_empty: Whether to allow empty querysets.
        extra_context: Additional context data.
        context_processors: Context processors to apply.
        template_object_name: The name of the object in the template.
        mimetype: Optional mimetype for the response.
        param: Optional parameters for form processing.

    Returns:
        HttpResponse: The rendered response.
    """
    try:
        form_instance = form_class(request.POST or None)
        if request.POST and form_instance.is_valid():
            queryset = (
                form_instance.Process(request, queryset, param)
                if param
                else form_instance.Process(request, queryset)
            )
            extra_context = extra_context or {}
            extra_context.update({"form": form_instance})
        elif table_always:
            extra_context = extra_context or {}
            extra_context.update({"form": form_instance})
            if hasattr(form_instance, "ProcessEmpty"):
                queryset = (
                    form_instance.ProcessEmpty(request, queryset, param)
                    if param
                    else form_instance.ProcessEmpty(request, queryset)
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
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}", status=500)


def direct_to_template(request, template, extra_context=None, mimetype=None, **kwargs):
    """Render a template directly with additional context.

    Args:
        request: The HTTP request object.
        template: The template to render.
        extra_context: Additional context data.
        mimetype: Optional mimetype for the response.
        **kwargs: Additional URL parameters.

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
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}", status=500)
