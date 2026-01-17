import asyncio
import contextlib
import datetime
import logging
import random
import typing
import zoneinfo

import pydantic
from redis import asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import LockError

from redis_timers import settings
from redis_timers.handler import Handler
from redis_timers.lock import consume_lock
from redis_timers.router import Router


if typing.TYPE_CHECKING:
    from redis.asyncio.client import Pipeline

logger = logging.getLogger(__name__)


TIMEZONE = zoneinfo.ZoneInfo("UTC")


class Timers:
    __slots__ = "context", "handlers_by_topics", "redis_client"

    def __init__(
        self,
        *,
        redis_client: Redis,  # type: ignore[type-arg]
        context: dict[str, typing.Any],
        routers: list[Router] | None = None,
    ) -> None:
        self.handlers_by_topics: dict[str, Handler[typing.Any]] = {}
        self.redis_client = redis_client
        self.context = context
        if routers:
            self.include_routers(*routers)

    def include_router(self, router: Router) -> None:
        for h in router.handlers:
            self.handlers_by_topics[h.topic] = h

    def include_routers(self, *routers: Router) -> None:
        for r in routers:
            self.include_router(r)

    @staticmethod
    def _convert_datetime_to_redis_format(datetime_point: datetime.datetime) -> str:
        return str(int(datetime_point.timestamp()))

    async def fetch_ready_timers(self, timestamp: datetime.datetime) -> list[str]:
        current_timestamp: typing.Final = self._convert_datetime_to_redis_format(timestamp)
        return await self.redis_client.zrangebyscore(
            settings.TIMERS_TIMELINE_KEY,
            "-inf",
            current_timestamp,
            withscores=False,
        )

    async def _handle_one_timer(self, timer_key: str) -> None:
        topic = timer_key.split(settings.TIMERS_SEPARATOR)[0]
        handler = self.handlers_by_topics.get(topic)
        if not handler:
            logger.error(f"Handler is not found, {timer_key=}")
            return

        raw_payload = await self.redis_client.hget(settings.TIMERS_PAYLOADS_KEY, timer_key)
        if not raw_payload:
            logger.debug(f"No payload found, seems like it was removed {timer_key=}")
            return

        try:
            payload = handler.schema.model_validate_json(raw_payload)
        except pydantic.ValidationError:
            logger.exception(f"Failed to parse payload, {timer_key=}, {raw_payload=}")
            return

        await handler.handler(payload, self.context)

    async def _handle_one_timer_with_lock(self, timer_key: str) -> None:
        lock = consume_lock(
            redis_client=self.redis_client,
            key=timer_key,
        )
        if await lock.locked():
            logger.debug(f"Timer is locked, {timer_key=}")
            return

        with contextlib.suppress(LockError):
            async with lock:
                await self._handle_one_timer(timer_key)
                await self._remove_timer_by_key(timer_key)

    async def handle_ready_timers(self) -> None:
        ready_timers = await self.fetch_ready_timers(timestamp=datetime.datetime.now(tz=TIMEZONE))
        tasks_number = 0
        async with asyncio.TaskGroup() as tg:
            for timer_key in ready_timers:
                tasks_number += 1
                if tasks_number > settings.TIMERS_CONCURRENT_PROCESSING_LIMIT:
                    break

                tg.create_task(self._handle_one_timer_with_lock(timer_key=timer_key))

    async def run_forever(self) -> None:  # pragma: no cover
        while True:
            try:
                await self.handle_ready_timers()
            except aioredis.RedisError:
                logger.exception("Timer haven't been consumed because of Redis error")
            await asyncio.sleep(
                settings.TIMERS_HANDLING_SLEEP
                * random.uniform(settings.TIMERS_HANDLING_JITTER_MIN_VALUE, settings.TIMERS_HANDLING_JITTER_MAX_VALUE),  # noqa: S311
            )

    def _find_handler(self, topic: str) -> Handler[typing.Any]:
        handler = self.handlers_by_topics.get(topic)
        if not handler:
            raise RuntimeError(f"Handler is not found, {topic=}")

        return handler

    async def set_timer(
        self, topic: str, timer_id: str, payload: pydantic.BaseModel, activation_period: datetime.timedelta
    ) -> None:
        handler = self._find_handler(topic)
        timer_key: typing.Final = handler.build_timer_key(timer_id)
        pipeline: Pipeline[str]
        async with self.redis_client.pipeline() as pipeline:
            timer_timestamp: typing.Final = self._convert_datetime_to_redis_format(
                datetime.datetime.now(tz=TIMEZONE) + activation_period
            )
            pipeline.zadd(settings.TIMERS_TIMELINE_KEY, {timer_key: timer_timestamp})
            pipeline.hset(settings.TIMERS_PAYLOADS_KEY, timer_key, payload.model_dump_json())
            await pipeline.execute()

    async def remove_timer(self, topic: str, timer_id: str) -> None:
        handler = self._find_handler(topic)
        timer_key: typing.Final = handler.build_timer_key(timer_id)
        await self._remove_timer_by_key(timer_key)

    async def _remove_timer_by_key(self, timer_key: str) -> None:
        async with self.redis_client.pipeline() as pipeline:
            pipeline.zrem(settings.TIMERS_TIMELINE_KEY, timer_key)
            pipeline.hdel(settings.TIMERS_PAYLOADS_KEY, timer_key)
            await pipeline.execute()

    async def fetch_all_timers(self) -> tuple[list[str], dict[str, str]]:
        timeline_keys = await self.redis_client.zrange(settings.TIMERS_TIMELINE_KEY, 0, -1)
        payloads_dict = await self.redis_client.hgetall(settings.TIMERS_PAYLOADS_KEY)
        return timeline_keys, payloads_dict
