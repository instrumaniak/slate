"""Tests for EventBus pub/sub implementation."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from slate.core.event_bus import EventBus
from slate.core.events import (
    FileOpenedEvent,
    FileSavedEvent,
    ThemeChangedEvent,
)


class TestEventBus:
    """Test EventBus class."""

    def test_event_bus_is_singleton(self):
        """EventBus should be a singleton."""
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2

    def test_subscribe(self):
        """EventBus should allow subscribing to events."""
        bus = EventBus()
        calls = []

        def handler(event: FileOpenedEvent) -> None:
            calls.append(event)

        bus.subscribe(FileOpenedEvent, handler)
        event = FileOpenedEvent(path="/test.py", content="test")
        bus.emit(event)

        assert len(calls) == 1
        assert calls[0].path == "/test.py"

    def test_emit_calls_multiple_handlers(self):
        """EventBus should call all handlers for an event type."""
        bus = EventBus()
        calls = []

        def handler1(event: FileOpenedEvent) -> None:
            calls.append(1)

        def handler2(event: FileOpenedEvent) -> None:
            calls.append(2)

        bus.subscribe(FileOpenedEvent, handler1)
        bus.subscribe(FileOpenedEvent, handler2)
        bus.emit(FileOpenedEvent(path="/test.py", content="test"))

        assert len(calls) == 2
        assert 1 in calls
        assert 2 in calls

    def test_unsubscribe(self):
        """EventBus should allow unsubscribing."""
        bus = EventBus()
        calls = []

        def handler(event: FileOpenedEvent) -> None:
            calls.append(event)

        bus.subscribe(FileOpenedEvent, handler)
        bus.emit(FileOpenedEvent(path="/test.py", content="test"))
        assert len(calls) == 1

        bus.unsubscribe(FileOpenedEvent, handler)
        bus.emit(FileOpenedEvent(path="/test2.py", content="test2"))
        assert len(calls) == 1

    def test_handlers_called_in_subscription_order(self):
        """Handlers should be called in order of subscription."""
        bus = EventBus()
        order = []

        def handler1(event: FileOpenedEvent) -> None:
            order.append(1)

        def handler2(event: FileOpenedEvent) -> None:
            order.append(2)

        def handler3(event: FileOpenedEvent) -> None:
            order.append(3)

        bus.subscribe(FileOpenedEvent, handler1)
        bus.subscribe(FileOpenedEvent, handler2)
        bus.subscribe(FileOpenedEvent, handler3)
        bus.emit(FileOpenedEvent(path="/test.py", content="test"))

        assert order == [1, 2, 3]

    def test_emit_ignores_other_event_types(self):
        """Emitting one event type should not trigger handlers for other types."""
        bus = EventBus()
        file_opened_calls = []
        file_saved_calls = []

        def file_opened_handler(event: FileOpenedEvent) -> None:
            file_opened_calls.append(event)

        def file_saved_handler(event: FileSavedEvent) -> None:
            file_saved_calls.append(event)

        bus.subscribe(FileOpenedEvent, file_opened_handler)
        bus.subscribe(FileSavedEvent, file_saved_handler)

        bus.emit(FileOpenedEvent(path="/test.py", content="test"))
        assert len(file_opened_calls) == 1
        assert len(file_saved_calls) == 0

    def test_thread_safety_concurrent_emit(self):
        """EventBus should handle concurrent emit calls."""
        bus = EventBus()
        calls = []
        lock = threading.Lock()
        start_event = threading.Event()

        def handler(event: FileOpenedEvent) -> None:
            with lock:
                calls.append(event)

        bus.subscribe(FileOpenedEvent, handler)

        def emit_events():
            start_event.wait()
            for i in range(50):
                bus.emit(FileOpenedEvent(path=f"/test{i}.py", content="test"))

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(emit_events) for _ in range(4)]
            start_event.set()
            for f in futures:
                f.result()

        assert len(calls) == 200

    def test_thread_safety_concurrent_subscribe_unsubscribe(self):
        """EventBus should handle concurrent subscribe/unsubscribe."""
        bus = EventBus()
        results = []
        lock = threading.Lock()

        def handler1(event: ThemeChangedEvent) -> None:
            with lock:
                results.append(1)

        def handler2(event: ThemeChangedEvent) -> None:
            with lock:
                results.append(2)

        def subscribe_handlers():
            bus.subscribe(ThemeChangedEvent, handler1)
            bus.subscribe(ThemeChangedEvent, handler2)

        thread1 = threading.Thread(target=subscribe_handlers)
        thread1.start()
        thread1.join()

        bus.emit(
            ThemeChangedEvent(color_mode="dark", resolved_is_dark=True, editor_scheme="default")
        )
        assert len(results) == 2
