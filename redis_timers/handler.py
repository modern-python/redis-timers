import dataclasses
import typing

import pydantic

from redis_timers import settings


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Handler[T: pydantic.BaseModel]:
    topic: str
    schema: type[T]
    handler: typing.Callable[[T], typing.Coroutine[None, None, None]]

    def build_timer_key(self, timer_id: str) -> str:
        return f"{self.topic}{settings.TIMERS_SEPARATOR}{timer_id}"
