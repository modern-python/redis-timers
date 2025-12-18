import typing

import pydantic


SchemaType = typing.TypeVar("SchemaType", bound=pydantic.BaseModel)
ContextType = dict[str, typing.Any]
HandlerType = typing.Callable[[SchemaType, ContextType], typing.Coroutine[None, None, None]]
