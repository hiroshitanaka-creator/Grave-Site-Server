from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from src.diary_processor import analyze_entry


@dataclass(frozen=True)
class ScheduledDiaryEvent:
    """Input event schema for scheduled diary processing."""

    user_id: str
    recipient_id: str
    calendar_id: str
    delivery_date: date
    memory_refs: tuple[str, ...]
    scheduled_at: datetime
    entry_text: str
    source: str

    @property
    def idempotency_key(self) -> str:
        return (
            f"{self.user_id}:{self.recipient_id}:{self.calendar_id}:"
            f"{self.delivery_date.isoformat()}"
        )


@dataclass(frozen=True)
class ParsedDiaryRecord:
    user_id: str
    idempotency_key: str
    scheduled_at: str
    source: str
    entry: str
    mood_tag: str
    topic_tag: str
    summary: str


@dataclass(frozen=True)
class ComposedMessage:
    idempotency_key: str
    recipient_id: str
    calendar_id: str
    delivery_date: str
    body: str


@dataclass(frozen=True)
class DeliveryResult:
    idempotency_key: str
    provider: str
    delivery_id: str
    status: str


class EventQueuePublisher(Protocol):
    """Interface for producer side (Scheduler -> Queue/Topic)."""

    def publish(self, event: ScheduledDiaryEvent) -> str:
        ...


class EventQueueSubscriber(Protocol):
    """Interface for consumer side (Queue/Topic -> Parser Pipeline)."""

    def acknowledge(self, event: ScheduledDiaryEvent) -> None:
        ...

    def retry_later(self, event: ScheduledDiaryEvent, reason: str) -> None:
        ...


class DiaryStorage(Protocol):
    def exists(self, idempotency_key: str) -> bool:
        ...

    def save(
        self,
        record: ParsedDiaryRecord,
        composed_message: ComposedMessage,
        delivery_result: DeliveryResult,
    ) -> None:
        ...


class NotificationUpdater(Protocol):
    def mark_processed(self, user_id: str, scheduled_at: datetime) -> None:
        ...

    def mark_skipped_duplicate(self, user_id: str, scheduled_at: datetime) -> None:
        ...


class ParseService(Protocol):
    def parse(self, event: ScheduledDiaryEvent) -> ParsedDiaryRecord:
        ...


class MessageComposer(Protocol):
    def compose(self, event: ScheduledDiaryEvent, record: ParsedDiaryRecord) -> ComposedMessage:
        ...


class CalendarPublisher(Protocol):
    def publish(self, message: ComposedMessage) -> DeliveryResult:
        ...


class DefaultParseService:
    """Gemini/OpenAI equivalent parser adapter."""

    def parse(self, event: ScheduledDiaryEvent) -> ParsedDiaryRecord:
        parsed = analyze_entry(event.entry_text, event.delivery_date.isoformat())
        return ParsedDiaryRecord(
            user_id=event.user_id,
            idempotency_key=event.idempotency_key,
            scheduled_at=event.scheduled_at.isoformat(),
            source=event.source,
            entry=parsed["entry"],
            mood_tag=parsed["mood_tag"],
            topic_tag=parsed["topic_tag"],
            summary=parsed["summary"],
        )


class PipelineRetryExceededError(RuntimeError):
    pass


class PublishStageError(RuntimeError):
    def __init__(self, failure_type: str, message: str) -> None:
        super().__init__(message)
        self.failure_type = failure_type


class DefaultMessageComposer:
    def compose(self, event: ScheduledDiaryEvent, record: ParsedDiaryRecord) -> ComposedMessage:
        return ComposedMessage(
            idempotency_key=event.idempotency_key,
            recipient_id=event.recipient_id,
            calendar_id=event.calendar_id,
            delivery_date=event.delivery_date.isoformat(),
            body=record.summary,
        )


class NoOpCalendarPublisher:
    def publish(self, message: ComposedMessage) -> DeliveryResult:
        return DeliveryResult(
            idempotency_key=message.idempotency_key,
            provider="noop-calendar",
            delivery_id=message.idempotency_key,
            status="published",
        )


class ScheduledDiaryPipeline:
    """Consumer pipeline: parse -> compose -> publish -> save -> ack with retries."""

    def __init__(
        self,
        parser: ParseService,
        composer: MessageComposer,
        publisher: CalendarPublisher,
        storage: DiaryStorage,
        notifier: NotificationUpdater,
        subscriber: EventQueueSubscriber,
        *,
        max_retries: int = 3,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        self._parser = parser
        self._composer = composer
        self._publisher = publisher
        self._storage = storage
        self._notifier = notifier
        self._subscriber = subscriber
        self._max_retries = max_retries

    def handle_event(self, event: ScheduledDiaryEvent) -> DeliveryResult | None:
        if self._storage.exists(event.idempotency_key):
            self._notifier.mark_skipped_duplicate(event.user_id, event.scheduled_at)
            self._subscriber.acknowledge(event)
            return None

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            stage = "parse"
            try:
                record = self._parser.parse(event)
                stage = "compose"
                message = self._composer.compose(event, record)
                stage = "publish"
                delivery_result = self._publisher.publish(message)
                stage = "save"
                self._storage.save(record, message, delivery_result)
                self._notifier.mark_processed(event.user_id, event.scheduled_at)
                self._subscriber.acknowledge(event)
                return delivery_result
            except Exception as exc:  # intentional: boundary retry handler
                last_error = exc
                if attempt < self._max_retries:
                    reason = f"attempt={attempt} stage={stage} error={exc}"
                    if stage == "publish" and isinstance(exc, PublishStageError):
                        reason += f" publish_failure_type={exc.failure_type}"
                    self._subscriber.retry_later(
                        event,
                        reason=reason,
                    )

        raise PipelineRetryExceededError(
            f"failed after {self._max_retries} attempts for key={event.idempotency_key}"
        ) from last_error


class InMemoryDiaryStorage:
    """Reference storage implementation for local runs/tests."""

    def __init__(self) -> None:
        self._records_by_key: dict[str, ParsedDiaryRecord] = {}
        self._messages_by_key: dict[str, ComposedMessage] = {}
        self._deliveries_by_key: dict[str, DeliveryResult] = {}

    def exists(self, idempotency_key: str) -> bool:
        return idempotency_key in self._records_by_key

    def save(
        self,
        record: ParsedDiaryRecord,
        composed_message: ComposedMessage,
        delivery_result: DeliveryResult,
    ) -> None:
        self._records_by_key[record.idempotency_key] = record
        self._messages_by_key[record.idempotency_key] = composed_message
        self._deliveries_by_key[record.idempotency_key] = delivery_result


class InMemoryEventBus(EventQueuePublisher, EventQueueSubscriber):
    """Queue/topic adapter placeholder to keep sender/consumer decoupled."""

    def __init__(self) -> None:
        self.published: list[ScheduledDiaryEvent] = []
        self.acked: list[str] = []
        self.retried: list[tuple[str, str]] = []

    def publish(self, event: ScheduledDiaryEvent) -> str:
        self.published.append(event)
        return event.idempotency_key

    def acknowledge(self, event: ScheduledDiaryEvent) -> None:
        self.acked.append(event.idempotency_key)

    def retry_later(self, event: ScheduledDiaryEvent, reason: str) -> None:
        self.retried.append((event.idempotency_key, reason))
