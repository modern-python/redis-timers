import typing

from redis.asyncio.lock import Lock


if typing.TYPE_CHECKING:
    from redis import asyncio as aioredis


REDIS_LOCK_LIFESPAN_IN_SECONDS: typing.Final = 30


def consume_lock(redis_client: "aioredis.Redis[str]", key: str) -> Lock:
    return Lock(
        redis_client,
        f"consume-lock--{key}",
        timeout=REDIS_LOCK_LIFESPAN_IN_SECONDS,
        blocking=False,
    )
