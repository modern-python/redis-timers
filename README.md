# Redis Timers

[![MyPy Strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/en/stable/getting_started.html#strict-mode-and-configuration)
[![Supported versions](https://img.shields.io/pypi/pyversions/redis-timers.svg)](https://pypi.python.org/pypi/redis-timers)
[![downloads](https://img.shields.io/pypi/dm/redis-timers.svg)](https://pypistats.org/packages/redis-timers)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/redis-timers)](https://github.com/modern-python/redis-timers/stargazers)

Redis Timers is a Python library that provides a robust framework for managing timed events using Redis as the backend.

It allows you to schedule timers that trigger handlers at specific times, with payloads automatically validated using Pydantic schemas.

## Features

- Schedule timers with custom payloads
- Automatic payload validation using Pydantic
- Distributed lock mechanism to prevent duplicate processing
- Topic-based routing for timer handlers
- Automatic cleanup of processed timers
- Built with asyncio for high performance

## 📦 [PyPi](https://pypi.org/project/redis-timers)

## 📝 [License](LICENSE)


## Installation

```bash
pip install redis-timers
```

## Quick Start

```python
import asyncio
import datetime
from redis import asyncio as aioredis
from pydantic import BaseModel

from redis_timers import Timers, Router

# Define your payload schema
class MyPayload(BaseModel):
    message: str
    count: int

# Create a router and register handlers
router = Router()

@router.handler(topic="my_topic", schema=MyPayload)
async def my_timer_handler(data: MyPayload, context: dict):
    print(f"Timer triggered: {data.message} (count: {data.count})")

# Initialize Redis client
redis_client = aioredis.Redis.from_url("redis://localhost:6379", decode_responses=True)

# Initialize timers
timers = Timers(redis_client=redis_client, context={"app_name": "my_app"})
timers.include_router(router)

# Schedule a timer
async def schedule_timer():
    payload = MyPayload(message="Hello, World!", count=42)
    await timers.set_timer(
        topic="my_topic",
        timer_id="unique_timer_id",
        payload=payload,
        activation_period=datetime.timedelta(minutes=5)
    )

# Run the timer processing loop
async def main():
    # Schedule a timer
    await schedule_timer()

    # Process timers continuously
    await timers.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

## Core Concepts

### Timers

The `Timers` class is the main interface for managing timed events. It connects to Redis and handles the scheduling, execution, and cleanup of timers.

### Router

The `Router` class is used to register timer handlers. Handlers are functions that get executed when a timer expires.

### Handlers

Handlers are async functions decorated with `@router.handler()` that process timer events. Each handler is associated with a topic and a Pydantic schema for payload validation.

### Payloads

Payloads are Pydantic models that contain the data associated with a timer. They are automatically validated when timers are processed.

## API Reference

### Timers

#### `Timers(redis_client, context={})`

Initialize a Timers instance.

- `redis_client`: An async Redis client instance
- `context`: A dictionary of context data passed to handlers

#### `timers.include_router(router)`

Include a router with its handlers.

#### `timers.include_routers(*routers)`

Include multiple routers.

#### `timers.set_timer(topic, timer_id, payload, activation_period)`

Schedule a timer.

- `topic`: The topic associated with the timer handler
- `timer_id`: A unique identifier for the timer
- `payload`: A Pydantic model instance containing the timer data
- `activation_period`: A timedelta specifying when the timer should trigger

#### `timers.remove_timer(topic, timer_id)`

Remove a scheduled timer.

#### `timers.handle_ready_timers()`

Process all timers that are ready to be triggered.

#### `timers.run_forever()`

Continuously process timers in a loop.

### Router

#### `Router()`

Create a new router instance.

#### `router.handler(topic, schema)`

Decorator for registering timer handlers.

- `topic`: The topic to associate with this handler
- `schema`: The Pydantic model class for payload validation

## Configuration

Redis Timers can be configured using environment variables:

- `TIMERS_TIMELINE_KEY`: Redis key for the sorted set storing timer timestamps (default: "timers_timeline")
- `TIMERS_PAYLOADS_KEY`: Redis key for the hash storing timer payloads (default: "timers_payloads")
- `TIMERS_HANDLING_SLEEP`: Base sleep time between timer processing cycles (default: 0.05 seconds)
- `TIMERS_HANDLING_JITTER_MIN_VALUE`: Minimum jitter multiplier (default: 0.5)
- `TIMERS_HANDLING_JITTER_MAX_VALUE`: Maximum jitter multiplier (default: 2.0)
- `TIMERS_CONCURRENT_PROCESSING_LIMIT`: Maximum number of timers processed concurrently (default: 5)
- `TIMERS_SEPARATOR`: Separator used between topic and timer ID (default: "--")

## How It Works

1. **Timer Scheduling**: When you call `set_timer()`, Redis Timers stores:
   - The timer's activation timestamp in a Redis sorted set (`timers_timeline`)
   - The timer's payload as JSON in a Redis hash (`timers_payloads`)
   - The timer key is constructed as `{topic}{separator}{timer_id}`

2. **Timer Processing**: The `run_forever()` method continuously:
   - Checks for timers that should be triggered (current timestamp >= activation timestamp)
   - Acquires a distributed lock to prevent duplicate processing
   - Validates the payload using the registered Pydantic schema
   - Calls the appropriate handler function
   - Removes the processed timer from Redis

3. **Distributed Locking**: Redis Timers uses Redis locks to ensure that:
   - The same timer isn't processed multiple times in distributed environments
   - Concurrent modifications to the same timer are prevented

## Requirements

- Python 3.13+
- Redis server
- Dependencies: `pydantic`, `redis`
