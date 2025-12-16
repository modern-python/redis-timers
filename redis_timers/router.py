import dataclasses
import typing

import pydantic

from redis_timers.handler import Handler


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Router:
    handlers: list[Handler[typing.Any]] = dataclasses.field(default_factory=list, init=False)

    def handler[T: pydantic.BaseModel](
        self,
        *,
        name: str | None = None,
        schema: type[T],
    ) -> typing.Callable[
        [typing.Callable[[T], typing.Coroutine[None, None, None]]],
        typing.Callable[[T], typing.Coroutine[None, None, None]],
    ]:
        def _decorator(
            func: typing.Callable[[T], typing.Coroutine[None, None, None]],
        ) -> typing.Callable[[T], typing.Coroutine[None, None, None]]:
            self.handlers.append(
                Handler(
                    topic=name or func.__name__,
                    schema=schema,
                    handler=func,
                )
            )
            return func

        return _decorator
