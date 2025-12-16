import typing

import pydantic

from redis_timers.router import Router


class SomeSchema(pydantic.BaseModel):
    message: str


class AnotherSchema(pydantic.BaseModel):
    count: int


def test_register_handler_with_name() -> None:
    router: typing.Final = Router()

    @router.handler(name="test_timer", schema=SomeSchema)
    async def test_handler(data: SomeSchema) -> None: ...

    assert len(router.handlers) == 1
    handler: typing.Final = router.handlers[0]
    assert handler.topic == "test_timer"
    assert handler.schema == SomeSchema
    assert handler.handler == test_handler


def test_register_handler_without_name() -> None:
    router: typing.Final = Router()

    @router.handler(schema=SomeSchema)
    async def my_timer_handler(data: SomeSchema) -> None: ...

    assert len(router.handlers) == 1
    handler: typing.Final = router.handlers[0]
    assert handler.topic == "my_timer_handler"
    assert handler.schema == SomeSchema
    assert handler.handler == my_timer_handler


def test_register_handler_multiple_handlers() -> None:
    router: typing.Final = Router()
    expected_handlers_count: typing.Final = 2

    @router.handler(name="handler1", schema=SomeSchema)
    async def handler1(data: SomeSchema) -> None: ...

    @router.handler(name="handler2", schema=AnotherSchema)
    async def handler2(data: AnotherSchema) -> None: ...

    assert len(router.handlers) == expected_handlers_count
    assert router.handlers[0].topic == "handler1"
    assert router.handlers[0].schema == SomeSchema
    assert router.handlers[0].handler == handler1
    assert router.handlers[1].topic == "handler2"
    assert router.handlers[1].schema == AnotherSchema
    assert router.handlers[1].handler == handler2
