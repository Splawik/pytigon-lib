from pytigon_lib.schviews.actions import *

# Pytest tests
import pytest
from django.test import RequestFactory


@pytest.fixture
def rf():
    return RequestFactory()


def test_new_row_ok(rf):
    request = rf.get("/")
    response = new_row_ok(request, 1, {})
    assert response.status_code == 200


def test_update_row_ok(rf):
    request = rf.get("/")
    response = update_row_ok(request, 1, {})
    assert response.status_code == 200


def test_delete_row_ok(rf):
    request = rf.get("/")
    response = delete_row_ok(request, 1, {})
    assert response.status_code == 200


def test_ok(rf):
    request = rf.get("/")
    response = ok(request)
    assert response.status_code == 200


def test_refresh(rf):
    request = rf.get("/")
    response = refresh(request)
    assert response.status_code == 200


def test_refresh_parent(rf):
    request = rf.get("/")
    response = refresh_parent(request)
    assert response.status_code == 200


def test_reload(rf):
    request = rf.get("/")
    response = reload(request, "new content")
    assert response.status_code == 200


def test_cancel(rf):
    request = rf.get("/")
    response = cancel(request)
    assert response.status_code == 200


def test_error(rf):
    request = rf.get("/")
    response = error(request, "error message")
    assert response.status_code == 400
