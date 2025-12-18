import dataclasses
import typing

import pydantic

from redis_timers import types
from redis_timers.handler import Handler


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Router:
    handlers: list[Handler[typing.Any]] = dataclasses.field(default_factory=list, init=False)

    def handler[T: pydantic.BaseModel](
        self,
        *,
        topic: str,
        schema: type[T],
    ) -> typing.Callable[[types.HandlerType[T]], types.HandlerType[T]]:
        def _decorator(func: types.HandlerType[T]) -> types.HandlerType[T]:
            self.handlers.append(
                Handler(
                    topic=topic,
                    schema=schema,
                    handler=func,
                )
            )
            return func

        return _decorator
