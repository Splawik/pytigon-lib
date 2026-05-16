# Pytest tests
from django import forms
from django.http import HttpResponse
from django.test import RequestFactory

from pytigon_lib.schviews.form_fun import *


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
