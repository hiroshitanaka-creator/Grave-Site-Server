from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import pytest

from src.workflows.scheduled_diary_pipeline import (
    ComposedMessage,
    DefaultMessageComposer,
    DefaultParseService,
    DeliveryResult,
    InMemoryDiaryStorage,
    InMemoryEventBus,
    ParsedDiaryRecord,
    PipelineRetryExceededError,
    PublishStageError,
    ScheduledDiaryPipeline,
    ScheduledDiaryEvent,
    NoOpCalendarPublisher,
)


class StubNotifier:
    def __init__(self) -> None:
        self.processed: list[tuple[str, datetime]] = []
        self.duplicates: list[tuple[str, datetime]] = []

    def mark_processed(self, user_id: str, scheduled_at: datetime) -> None:
        self.processed.append((user_id, scheduled_at))

    def mark_skipped_duplicate(self, user_id: str, scheduled_at: datetime) -> None:
        self.duplicates.append((user_id, scheduled_at))


class FlakyParseService:
    def __init__(self, fail_count: int) -> None:
        self.remaining_fail_count = fail_count

    def parse(self, event: ScheduledDiaryEvent) -> ParsedDiaryRecord:
        if self.remaining_fail_count > 0:
            self.remaining_fail_count -= 1
            raise RuntimeError("transient parser error")

        parsed = DefaultParseService().parse(event)
        return replace(parsed, summary="retry success")


class FlakyCalendarPublisher:
    def __init__(self, fail_count: int, failure_type: str = "quota") -> None:
        self.remaining_fail_count = fail_count
        self.failure_type = failure_type

    def publish(self, message: ComposedMessage) -> DeliveryResult:
        if self.remaining_fail_count > 0:
            self.remaining_fail_count -= 1
            raise PublishStageError(self.failure_type, "transient publish error")
        return DeliveryResult(
            idempotency_key=message.idempotency_key,
            provider="calendar-api",
            delivery_id=f"delivery-{message.idempotency_key}",
            status="published",
        )


@pytest.fixture
def event() -> ScheduledDiaryEvent:
    return ScheduledDiaryEvent(
        user_id="user-123",
        recipient_id="recipient-001",
        calendar_id="calendar-main",
        delivery_date=date.fromisoformat("2026-01-10"),
        memory_refs=("memory-1", "memory-2"),
        scheduled_at=datetime.fromisoformat("2026-01-10T08:00:00"),
        entry_text="今日は散歩して気分がよかった。",
        source="scheduler",
    )


def test_event_schema_has_idempotency_key(event: ScheduledDiaryEvent):
    assert event.idempotency_key == "user-123:recipient-001:calendar-main:2026-01-10"


def test_pipeline_processes_event_once(event: ScheduledDiaryEvent):
    storage = InMemoryDiaryStorage()
    bus = InMemoryEventBus()
    notifier = StubNotifier()
    pipeline = ScheduledDiaryPipeline(
        parser=DefaultParseService(),
        composer=DefaultMessageComposer(),
        publisher=NoOpCalendarPublisher(),
        storage=storage,
        notifier=notifier,
        subscriber=bus,
    )

    record = pipeline.handle_event(event)

    assert record is not None
    assert record.idempotency_key == event.idempotency_key
    assert bus.acked == [event.idempotency_key]
    assert notifier.processed == [(event.user_id, event.scheduled_at)]


def test_pipeline_skips_duplicate(event: ScheduledDiaryEvent):
    storage = InMemoryDiaryStorage()
    parsed = DefaultParseService().parse(event)
    message = DefaultMessageComposer().compose(event, parsed)
    result = NoOpCalendarPublisher().publish(message)
    storage.save(parsed, message, result)
    bus = InMemoryEventBus()
    notifier = StubNotifier()
    pipeline = ScheduledDiaryPipeline(
        parser=DefaultParseService(),
        composer=DefaultMessageComposer(),
        publisher=NoOpCalendarPublisher(),
        storage=storage,
        notifier=notifier,
        subscriber=bus,
    )

    record = pipeline.handle_event(event)

    assert record is None
    assert bus.acked == [event.idempotency_key]
    assert notifier.duplicates == [(event.user_id, event.scheduled_at)]


def test_pipeline_retries_then_succeeds(event: ScheduledDiaryEvent):
    storage = InMemoryDiaryStorage()
    bus = InMemoryEventBus()
    notifier = StubNotifier()
    pipeline = ScheduledDiaryPipeline(
        parser=FlakyParseService(fail_count=2),
        composer=DefaultMessageComposer(),
        publisher=NoOpCalendarPublisher(),
        storage=storage,
        notifier=notifier,
        subscriber=bus,
        max_retries=3,
    )

    record = pipeline.handle_event(event)

    assert record is not None
    assert record.status == "published"
    assert len(bus.retried) == 2


def test_pipeline_raises_when_retry_exhausted(event: ScheduledDiaryEvent):
    pipeline = ScheduledDiaryPipeline(
        parser=FlakyParseService(fail_count=5),
        composer=DefaultMessageComposer(),
        publisher=NoOpCalendarPublisher(),
        storage=InMemoryDiaryStorage(),
        notifier=StubNotifier(),
        subscriber=InMemoryEventBus(),
        max_retries=3,
    )

    with pytest.raises(PipelineRetryExceededError):
        pipeline.handle_event(event)


def test_pipeline_publish_failure_includes_failure_type(event: ScheduledDiaryEvent):
    bus = InMemoryEventBus()
    pipeline = ScheduledDiaryPipeline(
        parser=DefaultParseService(),
        composer=DefaultMessageComposer(),
        publisher=FlakyCalendarPublisher(fail_count=1, failure_type="permission"),
        storage=InMemoryDiaryStorage(),
        notifier=StubNotifier(),
        subscriber=bus,
        max_retries=2,
    )

    result = pipeline.handle_event(event)

    assert result is not None
    assert len(bus.retried) == 1
    _, reason = bus.retried[0]
    assert "stage=publish" in reason
    assert "publish_failure_type=permission" in reason
