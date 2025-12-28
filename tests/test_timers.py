import datetime
import logging
import os
import typing
from collections.abc import AsyncGenerator

import pydantic
import pytest
from redis import asyncio as aioredis

from redis_timers import Timers, consume_lock, settings
from redis_timers.router import Router


# Constants for test values
READY_TIMER_COUNT = 42
MULTIPLE_TIMERS_COUNT = 2
DUPLICATE_TIMER_COUNT = 2


class SomePayloadModel(pydantic.BaseModel):
    message: str
    count: int


class AnotherPayloadModel(pydantic.BaseModel):
    value: str


class HandlerResults:
    def __init__(self) -> None:
        self.results: list[SomePayloadModel | AnotherPayloadModel] = []

    def add_result(self, result: SomePayloadModel | AnotherPayloadModel) -> None:
        self.results.append(result)

    def clear(self) -> None:
        self.results.clear()


@pytest.fixture
async def redis_client() -> AsyncGenerator["aioredis.Redis[str]"]:
    client = aioredis.Redis.from_url(url=os.getenv("REDIS_URL", ""), decode_responses=True)
    try:
        await client.delete(settings.TIMERS_TIMELINE_KEY, settings.TIMERS_PAYLOADS_KEY)
        yield client
    finally:
        await client.aclose()  # type: ignore[attr-defined]


@pytest.fixture
async def handler_results() -> AsyncGenerator[HandlerResults]:
    results = HandlerResults()
    yield results
    results.clear()


@pytest.fixture
def timers_instance(redis_client: "aioredis.Redis[str]", handler_results: HandlerResults) -> Timers:
    router1 = Router()

    @router1.handler(topic="some_topic", schema=SomePayloadModel)
    async def some_handler(data: SomePayloadModel, context: dict[str, typing.Any]) -> None:
        handler_results.add_result(data)
        assert context["some_key"] == "some_value"

    router2 = Router()

    @router2.handler(topic="another_topic", schema=AnotherPayloadModel)
    async def another_handler(data: AnotherPayloadModel, context: dict[str, typing.Any]) -> None:
        handler_results.add_result(data)
        assert context["some_key"] == "some_value"

    timers = Timers(redis_client=redis_client, context={"some_key": "some_value"}, routers=[router1])
    timers.include_routers(router2)

    return timers


async def test_set_and_remove_timer(timers_instance: Timers) -> None:
    payload = SomePayloadModel(message="test", count=1)
    await timers_instance.set_timer(
        topic="some_topic", timer_id="test_timer_1", payload=payload, activation_period=datetime.timedelta(seconds=1)
    )

    # Check that timer exists in Redis
    timeline_keys, payloads_dict = await timers_instance.fetch_all_timers()
    assert len(timeline_keys) == 1
    timer_key = timeline_keys[0]
    assert timer_key == "some_topic--test_timer_1"

    # Check payloads has the timer data
    assert timer_key in payloads_dict
    payload_data = payloads_dict[timer_key]
    parsed_payload = SomePayloadModel.model_validate_json(payload_data)
    assert parsed_payload == payload

    # Remove the timer
    await timers_instance.remove_timer(topic="some_topic", timer_id="test_timer_1")

    # Check that timer is removed from Redis
    timeline_keys, payloads_dict = await timers_instance.fetch_all_timers()
    assert not timeline_keys
    assert not payloads_dict


async def test_set_undefined_timer(timers_instance: Timers) -> None:
    payload = SomePayloadModel(message="test", count=1)
    with pytest.raises(RuntimeError, match="Handler is not found, topic='wrong_topic'"):
        await timers_instance.set_timer(
            topic="wrong_topic",
            timer_id="test_timer_1",
            payload=payload,
            activation_period=datetime.timedelta(seconds=1),
        )


async def test_handle_ready_timers(timers_instance: Timers, handler_results: HandlerResults) -> None:
    payload = SomePayloadModel(message="ready_timer", count=42)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="ready_timer_1",
        payload=payload,
        activation_period=datetime.timedelta(seconds=0),  # Ready immediately
    )

    # Handle ready timers
    await timers_instance.handle_ready_timers()

    # Check that the handler was called
    assert handler_results.results
    assert len(handler_results.results) == 1
    result = handler_results.results[0]
    assert isinstance(result, SomePayloadModel)
    assert result == payload

    # Check that timer was removed from Redis
    timeline_keys, payloads_dict = await timers_instance.fetch_all_timers()
    assert not timeline_keys
    assert not payloads_dict


async def test_handle_ready_timers_with_zero_limit(timers_instance: Timers, handler_results: HandlerResults) -> None:
    old_value = settings.TIMERS_CONCURRENT_PROCESSING_LIMIT
    settings.TIMERS_CONCURRENT_PROCESSING_LIMIT = 0

    try:
        payload = SomePayloadModel(message="ready_timer", count=42)
        await timers_instance.set_timer(
            topic="some_topic",
            timer_id="ready_timer_1",
            payload=payload,
            activation_period=datetime.timedelta(seconds=0),  # Ready immediately
        )

        # Handle ready timers
        await timers_instance.handle_ready_timers()

        # Check that the handler was not called
        assert len(handler_results.results) == 0

        # Check that timer was not removed from Redis
        timeline_keys, payloads_dict = await timers_instance.fetch_all_timers()
        assert timeline_keys
        assert payloads_dict
    finally:
        settings.TIMERS_CONCURRENT_PROCESSING_LIMIT = old_value


async def test_handle_ready_timer_no_handler(timers_instance: Timers, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    payload = SomePayloadModel(message="ready_timer", count=42)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="ready_timer_1",
        payload=payload,
        activation_period=datetime.timedelta(seconds=0),  # Ready immediately
    )
    del timers_instance.handlers_by_topics["some_topic"]
    await timers_instance.handle_ready_timers()

    assert len(caplog.records) == 1
    assert "Handler is not found" in caplog.records[0].message


async def test_handle_ready_timer_no_payload(timers_instance: Timers, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    payload = SomePayloadModel(message="ready_timer", count=42)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="ready_timer_1",
        payload=payload,
        activation_period=datetime.timedelta(seconds=0),  # Ready immediately
    )
    await timers_instance.redis_client.hdel(settings.TIMERS_PAYLOADS_KEY, "some_topic--ready_timer_1")
    await timers_instance.handle_ready_timers()

    assert len(caplog.records) == 1
    assert "No payload found" in caplog.records[0].message


async def test_handle_ready_timer_invalid_payload(timers_instance: Timers, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    payload = SomePayloadModel(message="ready_timer", count=42)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="ready_timer_1",
        payload=payload,
        activation_period=datetime.timedelta(seconds=0),  # Ready immediately
    )
    await timers_instance.redis_client.hset(settings.TIMERS_PAYLOADS_KEY, "some_topic--ready_timer_1", "{}")
    await timers_instance.handle_ready_timers()

    assert len(caplog.records) == 1
    assert "Failed to parse payload" in caplog.records[0].message


async def test_handle_ready_timer_locked(timers_instance: Timers, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    payload = SomePayloadModel(message="ready_timer", count=42)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="ready_timer_1",
        payload=payload,
        activation_period=datetime.timedelta(seconds=0),  # Ready immediately
    )
    lock = consume_lock(
        redis_client=timers_instance.redis_client,
        key="some_topic--ready_timer_1",
    )
    async with lock:
        await timers_instance.handle_ready_timers()

    assert len(caplog.records) == 1
    assert "Timer is locked" in caplog.records[0].message


async def test_handle_multiple_ready_timers(timers_instance: Timers, handler_results: HandlerResults) -> None:
    payload1 = SomePayloadModel(message="timer_1", count=1)
    payload2 = AnotherPayloadModel(value="timer_2")

    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="multi_timer_1",
        payload=payload1,
        activation_period=datetime.timedelta(seconds=0),
    )

    await timers_instance.set_timer(
        topic="another_topic",
        timer_id="multi_timer_2",
        payload=payload2,
        activation_period=datetime.timedelta(seconds=0),
    )

    await timers_instance.handle_ready_timers()

    assert len(handler_results.results) == 2


async def test_timer_not_ready_yet(timers_instance: Timers, handler_results: HandlerResults) -> None:
    payload = SomePayloadModel(message="future_timer", count=99)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="future_timer_1",
        payload=payload,
        activation_period=datetime.timedelta(seconds=10),
    )

    await timers_instance.handle_ready_timers()

    assert len(handler_results.results) == 0
    timeline_keys, payloads_dict = await timers_instance.fetch_all_timers()
    assert len(timeline_keys) == 1
    timer_key = "some_topic--future_timer_1"
    assert timer_key in payloads_dict


async def test_remove_nonexistent_timer(timers_instance: Timers) -> None:
    await timers_instance.remove_timer(topic="some_topic", timer_id="nonexistent_timer")


async def test_set_timer_with_invalid_topic(timers_instance: Timers) -> None:
    payload = SomePayloadModel(message="test", count=1)

    with pytest.raises(RuntimeError, match="Handler is not found"):
        await timers_instance.set_timer(
            topic="invalid_topic",
            timer_id="test_timer_1",
            payload=payload,
            activation_period=datetime.timedelta(seconds=1),
        )


async def test_remove_timer_with_invalid_topic(timers_instance: Timers) -> None:
    with pytest.raises(RuntimeError, match="Handler is not found"):
        await timers_instance.remove_timer(topic="invalid_topic", timer_id="test_timer_1")


async def test_empty_timeline_handling(timers_instance: Timers, handler_results: HandlerResults) -> None:
    await timers_instance.handle_ready_timers()
    assert len(handler_results.results) == 0


async def test_duplicate_timer_replacement(timers_instance: Timers, handler_results: HandlerResults) -> None:
    payload1 = SomePayloadModel(message="first", count=1)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="duplicate_timer",
        payload=payload1,
        activation_period=datetime.timedelta(seconds=10),  # Far in future
    )

    payload2 = SomePayloadModel(message="second", count=2)
    await timers_instance.set_timer(
        topic="some_topic",
        timer_id="duplicate_timer",
        payload=payload2,
        activation_period=datetime.timedelta(seconds=0),  # Ready immediately
    )

    await timers_instance.handle_ready_timers()

    assert len(handler_results.results) == 1
    result = handler_results.results[0]
    assert isinstance(result, SomePayloadModel)
    assert result == payload2
