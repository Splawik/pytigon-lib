from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_cache():
    with patch("django.core.cache.cache") as mock:
        yield mock


class TestCommunicationBasePublisher:
    def test_send_event_no_op(self):
        from pytigon_lib.schtasks.publish import CommunicationBasePublisher

        pub = CommunicationBasePublisher()
        assert pub.send_event("data") is None

    def test_close_no_op(self):
        from pytigon_lib.schtasks.publish import CommunicationBasePublisher

        pub = CommunicationBasePublisher()
        assert pub.close() is None

    def test_context_manager_enter_returns_self(self):
        from pytigon_lib.schtasks.publish import CommunicationBasePublisher

        pub = CommunicationBasePublisher()
        with pub as p:
            assert p is pub

    def test_context_manager_calls_close_on_exit(self):
        from pytigon_lib.schtasks.publish import CommunicationBasePublisher

        pub = CommunicationBasePublisher()
        pub.close = MagicMock()
        with pub:
            pass
        pub.close.assert_called_once()


class TestCommunicationByCachePublisher:
    def test_init_sets_cache_count_to_zero(self):
        from pytigon_lib.schtasks.publish import DEFAULT_TIMEOUT, CommunicationByCachePublisher

        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            CommunicationByCachePublisher("test-id")
            mock.set.assert_called_once_with(
                "process_events_test-id_count", 0, timeout=DEFAULT_TIMEOUT
            )

    def test_send_event_increments_count_and_stores_value(self):
        from pytigon_lib.schtasks.publish import DEFAULT_TIMEOUT, CommunicationByCachePublisher

        mock = MagicMock()
        mock.incr.return_value = 1
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            pub = CommunicationByCachePublisher("test-id")
            pub.send_event("hello")
            mock.incr.assert_called_with("process_events_test-id_count")
            mock.set.assert_called_with(
                "process_events_test-id_value_0", "hello", timeout=DEFAULT_TIMEOUT
            )

    def test_send_event_multiple_appends(self):
        from pytigon_lib.schtasks.publish import CommunicationByCachePublisher

        mock = MagicMock()
        mock.incr.side_effect = [1, 2]
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            pub = CommunicationByCachePublisher("test-id")
            pub.send_event("first")
            pub.send_event("second")
            assert mock.set.call_count == 3

    def test_close_sends_end_marker(self):
        from pytigon_lib.schtasks.publish import DEFAULT_TIMEOUT, CommunicationByCachePublisher

        mock = MagicMock()
        mock.incr.return_value = 5
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            pub = CommunicationByCachePublisher("test-id")
            pub.close()
            mock.set.assert_called_with(
                "process_events_test-id_value_4",
                "$$$END$$$",
                timeout=DEFAULT_TIMEOUT,
            )

    def test_context_manager_calls_close(self):
        from pytigon_lib.schtasks.publish import CommunicationByCachePublisher

        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            pub = CommunicationByCachePublisher("test-id")
            pub.close = MagicMock()
            with pub:
                pass
            pub.close.assert_called_once()


class TestCommunicationBaseReceiver:
    def test_init_stores_id_and_observer(self):
        from pytigon_lib.schtasks.publish import CommunicationBaseReceiver

        observer = MagicMock()
        receiver = CommunicationBaseReceiver("recv-id", observer)
        assert receiver.id == "recv-id"
        assert receiver.observer is observer

    def test_init_without_observer(self):
        from pytigon_lib.schtasks.publish import CommunicationBaseReceiver

        receiver = CommunicationBaseReceiver("recv-id")
        assert receiver.observer is None

    def test_handle_start_calls_observer(self):
        from pytigon_lib.schtasks.publish import CommunicationBaseReceiver

        observer = MagicMock()
        receiver = CommunicationBaseReceiver("recv-id", observer)
        receiver.handle_start()
        observer.handle_start.assert_called_once()

    def test_handle_start_no_observer(self):
        from pytigon_lib.schtasks.publish import CommunicationBaseReceiver

        receiver = CommunicationBaseReceiver("recv-id")
        receiver.handle_start()

    def test_handle_event_calls_observer(self):
        from pytigon_lib.schtasks.publish import CommunicationBaseReceiver

        observer = MagicMock()
        receiver = CommunicationBaseReceiver("recv-id", observer)
        receiver.handle_event("data")
        observer.handle_event.assert_called_once_with("data")

    def test_handle_end_calls_observer(self):
        from pytigon_lib.schtasks.publish import CommunicationBaseReceiver

        observer = MagicMock()
        receiver = CommunicationBaseReceiver("recv-id", observer)
        receiver.handle_end()
        observer.handle_end.assert_called_once()


class TestCommunicationByCacheReceiver:
    def test_init_sets_defaults(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            assert receiver.process_events_count == 0
            assert receiver.started is False

    def test_process_returns_false_when_cache_empty_and_not_started(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        mock.get.return_value = None
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            result = receiver.process()
            assert result is False

    def test_process_starts_when_event_count_available(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        mock.get.return_value = 1
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            receiver.handle_start = MagicMock()
            receiver.process()
            assert receiver.started is True
            receiver.handle_start.assert_called_once()

    def test_process_handles_events_and_returns_true_for_new_events(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        mock.get.side_effect = (
            lambda key, default=None: {"process_events_recv-id_count": 2}.get(key, None)
        )
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            receiver.started = True
            receiver.handle_event = MagicMock()
            result = receiver.process()
            assert result is True
            assert receiver.handle_event.call_count > 0

    def test_process_handles_end_marker_and_removes_caches(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        mock.get.side_effect = lambda key, default=None: {
            "process_events_recv-id_count": 1,
            "process_events_recv-id_value_0": "$$$END$$$",
        }.get(key, None)
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            receiver.started = True
            receiver.handle_end = MagicMock()
            receiver._remove_caches = MagicMock()
            result = receiver.process()
            assert result is True
            receiver.handle_end.assert_called_once()
            receiver._remove_caches.assert_called_once()

    def test_process_no_new_events_returns_false(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        mock.get.return_value = 3
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            receiver.started = True
            receiver.process_events_count = 3
            result = receiver.process()
            assert result is False

    def test_remove_caches_deletes_all_keys(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        mock.get.return_value = 3
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            receiver._remove_caches()
            assert mock.delete.call_count == 4

    def test_handle_start_no_observer(self):
        from pytigon_lib.schtasks.publish import CommunicationByCacheReceiver

        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            receiver = CommunicationByCacheReceiver("recv-id")
            receiver.handle_start()


class TestPublishDecorator:
    def test_publish_returns_decorator(self):
        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            from pytigon_lib.schtasks.publish import publish

            dec = publish()
            assert callable(dec)

    def test_decorator_wraps_function_with_publisher(self):
        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            from pytigon_lib.schtasks.publish import CommunicationByCachePublisher, publish

            @publish("test-group")
            def my_func(cproxy=None, **kwargs):
                return cproxy

            result = my_func(task_publish_id="123")
            assert isinstance(result, CommunicationByCachePublisher)
            assert result.id == "test-group__123"

    def test_decorator_without_task_publish_id_uses_default_id(self):
        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            from pytigon_lib.schtasks.publish import CommunicationByCachePublisher, publish

            @publish("default-group")
            def my_func(cproxy=None):
                return cproxy

            result = my_func()
            assert isinstance(result, CommunicationByCachePublisher)
            assert result.id == "default-group"

    def test_decorator_passes_original_args(self):
        mock = MagicMock()
        with patch("pytigon_lib.schtasks.publish.cache", mock):
            from pytigon_lib.schtasks.publish import CommunicationByCachePublisher, publish

            @publish()
            def my_func(x, y, cproxy=None, **kwargs):
                return (x, y, cproxy)

            result = my_func(1, 2, task_publish_id="abc")
            assert result[0] == 1
            assert result[1] == 2
            assert isinstance(result[2], CommunicationByCachePublisher)
