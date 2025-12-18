import dataclasses

import pydantic

from redis_timers import settings, types


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Handler[T: pydantic.BaseModel]:
    topic: str
    schema: type[T]
    handler: types.HandlerType[T]

    def build_timer_key(self, timer_id: str) -> str:
        return f"{self.topic}{settings.TIMERS_SEPARATOR}{timer_id}"
