"""EventBus pub/sub implementation - Pure Python, zero GTK."""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from contextlib import suppress
from typing import TYPE_CHECKING

from slate.core.events import BaseEvent

if TYPE_CHECKING:
    from collections import defaultdict


class EventBus:
    """Thread-safe pub/sub event bus (singleton)."""

    _instance: EventBus | None = None
    _lock: threading.Lock | None = None
    _handlers: defaultdict[type[BaseEvent], list[Callable[[BaseEvent], None]]]
    _handler_lock: threading.Lock

    def __new__(cls) -> EventBus:
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._handlers = defaultdict(list)
                    cls._instance._handler_lock = threading.Lock()
        return cls._instance

    def subscribe(self, event_type: type[BaseEvent], handler: Callable[[BaseEvent], None]) -> None:
        """Register handler for event_type. Handlers called in subscription order."""
        with self._handler_lock:
            self._handlers[event_type].append(handler)

    def emit(self, event: BaseEvent) -> None:
        """Call all handlers registered for event's type."""
        event_type = type(event)
        with self._handler_lock:
            handlers = list(self._handlers.get(event_type, []))

        for handler in handlers:
            handler(event)

    def unsubscribe(
        self, event_type: type[BaseEvent], handler: Callable[[BaseEvent], None]
    ) -> None:
        """Remove handler from event_type."""
        with self._handler_lock:
            if event_type in self._handlers:
                with suppress(ValueError):
                    self._handlers[event_type].remove(handler)
