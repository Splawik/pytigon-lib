"""schviews views package."""

from .create_view import _create_create_view
from .delete_view import _create_delete_view
from .detail_view import _create_detail_view
from .list_view import _create_list_view
from .update_view import _create_update_view

__all__ = [
    "_create_create_view",
    "_create_delete_view",
    "_create_detail_view",
    "_create_list_view",
    "_create_update_view",
]
