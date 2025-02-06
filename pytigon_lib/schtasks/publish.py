from django.core.cache import cache
from typing import Optional, Callable, Any

DEFAULT_TIMEOUT = 60 * 60


class CommunicationBasePublisher:
    """Base class for communication publishers."""

    def send_event(self, value: Any) -> None:
        """Send an event with the given value."""
        pass

    def close(self) -> None:
        """Close the publisher."""
        pass

    def __enter__(self) -> "CommunicationBasePublisher":
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager."""
        self.close()


class CommunicationByCachePublisher(CommunicationBasePublisher):
    """Publisher that uses Django cache for communication."""

    def __init__(self, id: str) -> None:
        """Initialize the publisher with a unique ID."""
        self.id = id
        cache.set(f"process_events_{self.id}_count", 0, timeout=DEFAULT_TIMEOUT)

    def send_event(self, value: Any) -> None:
        """Send an event and store it in the cache."""
        event_count = cache.incr(f"process_events_{self.id}_count")
        cache.set(
            f"process_events_{self.id}_value_{event_count - 1}",
            value,
            timeout=DEFAULT_TIMEOUT,
        )

    def close(self) -> None:
        """Close the publisher and mark the end of events."""
        event_count = cache.incr(f"process_events_{self.id}_count")
        cache.set(
            f"process_events_{self.id}_value_{event_count - 1}",
            "$$$END$$$",
            timeout=DEFAULT_TIMEOUT,
        )


class CommunicationBaseReceiver:
    """Base class for communication receivers."""

    def __init__(self, id: str, observer: Optional[Any] = None) -> None:
        """Initialize the receiver with a unique ID and an optional observer."""
        self.id = id
        self.observer = observer

    def process(self) -> bool:
        """Process incoming events."""
        pass

    def handle_start(self) -> None:
        """Handle the start of event processing."""
        if self.observer:
            self.observer.handle_start()

    def handle_event(self, value: Any) -> None:
        """Handle an incoming event."""
        if self.observer:
            self.observer.handle_event(value)

    def handle_end(self) -> None:
        """Handle the end of event processing."""
        if self.observer:
            self.observer.handle_end()


class CommunicationByCacheReceiver(CommunicationBaseReceiver):
    """Receiver that uses Django cache for communication."""

    def __init__(self, id: str, observer: Optional[Any] = None) -> None:
        """Initialize the receiver with a unique ID and an optional observer."""
        super().__init__(id, observer)
        self.process_events_count = 0
        self.started = False

    def _remove_caches(self) -> None:
        """Remove cached events related to this receiver."""
        event_count = cache.get(f"process_events_{self.id}_count", 0)
        for i in range(event_count):
            cache.delete(f"process_events_{self.id}_value_{i}")
        cache.delete(f"process_events_{self.id}_count")

    def process(self) -> bool:
        """Process incoming events from the cache."""
        event_count = cache.get(f"process_events_{self.id}_count", None)

        if not self.started:
            if event_count is not None:
                self.started = True
                self.handle_start()
            else:
                return False

        if event_count != self.process_events_count:
            for i in range(self.process_events_count, event_count):
                value = cache.get(f"process_events_{self.id}_value_{i}", "")
                if value == "$$$END$$$":
                    self.handle_end()
                    self._remove_caches()
                    return True
                self.handle_event(value)

            self.process_events_count = event_count
            return True

        return False


def publish(task_publish_group: str = "default") -> Callable:
    """Decorator to publish events using a cache-based publisher."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            task_publish_id = kwargs.pop("task_publish_id", None)
            publisher_id = (
                f"{task_publish_group}__{task_publish_id}"
                if task_publish_id
                else task_publish_group
            )

            with CommunicationByCachePublisher(publisher_id) as cproxy:
                kwargs["cproxy"] = cproxy
                return func(*args, **kwargs)

        return wrapper

    return decorator
