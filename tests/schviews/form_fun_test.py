from pytigon_lib.schviews.form_fun import *

# Pytest tests
import pytest
from django.test import RequestFactory
from django import forms
from django.http import HttpResponse


class TestForm(forms.Form):
    name = forms.CharField()

    def process(self, request):
        return HttpResponse("test")


def test_form_view():
    factory = RequestFactory()
    request = factory.post("/", {"name": "test"})
    response = form(request, "test_app", TestForm, "template.html")
    assert response.content == b"test"
    assert response.status_code == 200
