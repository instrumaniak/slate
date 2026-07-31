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
    _pending: defaultdict[type[BaseEvent], list[BaseEvent]]
    _pending_lock: threading.Lock
    _flush_scheduled: bool

    def __new__(cls) -> EventBus:
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._handlers = defaultdict(list)
                    cls._instance._handler_lock = threading.Lock()
                    cls._instance._pending = defaultdict(list)
                    cls._instance._pending_lock = threading.Lock()
                    cls._instance._flush_scheduled = False
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

    def emit_batched(self, event: BaseEvent) -> None:
        """Queue event for batched emission on next GLib idle cycle.

        Events are collected and dispatched together to reduce UI redraws
        when many events fire in rapid succession (e.g., 500-file git status).
        GLib is lazily imported to keep this module GTK-free at module level.

        Args:
            event: The event to queue for batched emission.
        """
        with self._pending_lock:
            self._pending[type(event)].append(event)
            if self._flush_scheduled:
                return
            self._flush_scheduled = True
        try:
            from gi.repository import GLib  # Lazy import — core/ stays GTK-free

            GLib.idle_add(self._flush_pending, priority=GLib.PRIORITY_LOW)
        except Exception:
            with self._pending_lock:
                self._flush_scheduled = False
            raise

    def _flush_pending(self) -> bool:
        """Dispatch all queued events to their handlers.

        Called once per GLib idle cycle. Atomically swaps the pending queue
        so new events queued during dispatch go into the next batch.

        Returns:
            False — tells GLib not to repeat the idle callback.
        """
        with self._pending_lock:
            pending = self._pending
            self._pending = defaultdict(list)
            self._flush_scheduled = False

        for event_type, events in pending.items():
            with self._handler_lock:
                handlers = list(self._handlers.get(event_type, []))
            for event in events:
                for handler in handlers:
                    handler(event)
        return False

    def unsubscribe(
        self, event_type: type[BaseEvent], handler: Callable[[BaseEvent], None]
    ) -> None:
        """Remove handler from event_type."""
        with self._handler_lock:
            if event_type in self._handlers:
                with suppress(ValueError):
                    self._handlers[event_type].remove(handler)
