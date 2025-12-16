# Project Context for Agents

## Project Overview

This is a Python library called `redis-timers` that provides a framework for managing timed events using Redis as the backend. The library allows developers to schedule timers that trigger handlers at specific times, with payloads that are automatically validated using Pydantic schemas.

### Key Components

1. **Timers** - Main class that manages timer scheduling and execution
2. **Router** - Registration system for timer handlers
3. **Handlers** - Functions that are triggered when timers expire
4. **Locking System** - Ensures timers are processed only once even in distributed environments
5. **Settings** - Configuration for Redis keys and separators

### Technologies Used

- **Python 3.13** - Primary programming language
- **Redis** - Backend storage for timer data
- **Pydantic** - Data validation for timer payloads
- **AsyncIO** - Asynchronous programming model
- **Docker** - Containerization for development and deployment
- **uv** - Python package manager and project management
- **Ruff** - Code linting and formatting
- **MyPy** - Static type checking
- **Pytest** - Testing framework

## Project Structure

```
redis-timers/
├── redis_timers/           # Main library code
│   ├── __init__.py         # Package initialization
│   ├── handler.py          # Timer handler definitions
│   ├── lock.py             # Redis-based locking mechanisms
│   ├── router.py           # Router for registering handlers
│   ├── settings.py         # Configuration settings
│   ├── timers.py           # Core timer functionality
│   └── py.typed            # Type checking marker
├── tests/                  # Unit tests
├── Dockerfile              # Container definition
├── docker-compose.yml      # Development environment setup
├── Justfile                # Task runner commands
├── pyproject.toml          # Project configuration
├── poetry.lock             # Dependency lock file
└── uv.lock                 # Alternative dependency lock file
```

## Building and Running

### Development Environment Setup

1. Install dependencies:
   ```bash
   just install
   ```

2. Run tests:
   ```bash
   just test
   ```

3. Lint and format code:
   ```bash
   just lint
   ```

4. Build Docker image:
   ```bash
   just build
   ```

### Running the Application

The library is designed to be used as a dependency in other projects. To use it:

1. Import the necessary components:
   ```python
   from redis_timers import Timers, Router
   ```

2. Create routers and register handlers:
   ```python
   router = Router()
   
   @router.handler(schema=MySchema)
   async def my_timer_handler(data: MySchema):
       # Handle timer event
       pass
   ```

3. Initialize timers with a Redis client:
   ```python
   timers = Timers(redis_client=redis_client)
   timers.include_router(router)
   ```

4. Run the timer processing loop:
   ```python
   await timers.run_forever()
   ```

## Development Conventions

### Code Style

- Follow PEP 8 coding standards
- Use type hints for all function parameters and return values
- Use Ruff for linting and formatting
- Maintain 120 character line length limit
- Use dataclasses with `kw_only=True, slots=True, frozen=True` for immutable objects

### Testing

- Use pytest for unit testing
- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test function names
- Test both positive and negative cases

### Documentation

- Use docstrings for all public functions and classes
- Follow Google-style docstring format
- Document parameter types and return values
- Include usage examples for complex functionality

### Git Workflow

- Create feature branches for new functionality
- Write clear, concise commit messages
- Keep commits focused on single changes
- Rebase on main branch before merging
- Ensure all tests pass before pushing

## Key Features

### Timer Scheduling

Timers can be scheduled with:
- A topic identifier
- A unique timer ID
- A Pydantic model payload
- An activation period (timedelta)

```python
await timers.set_timer(
    topic="my_topic",
    timer_id="unique_id",
    payload=MyPayload(message="Hello"),
    activation_period=timedelta(minutes=5)
)
```

### Handler Registration

Handlers are registered using decorators:

```python
@router.handler(name="custom_name", schema=MySchema)
async def my_handler(data: MySchema):
    # Process timer event
    pass
```

If no name is provided, the function name is used as the topic.

### Distributed Locking

The library implements two types of locks:
1. **Timer Lock** - Prevents concurrent modifications to the same timer
2. **Consume Lock** - Ensures timers are processed only once in distributed environments

### Automatic Cleanup

Processed timers are automatically removed from Redis to prevent accumulation of stale data.

## Configuration

Environment variables can be used to configure Redis key names:
- `TIMERS_TIMELINE_KEY` - Key for the Redis sorted set storing timer timestamps (default: "timers_timeline")
- `TIMERS_PAYLOADS_KEY` - Key for the Redis hash storing timer payloads (default: "timers_payloads")
- `TIMERS_SEPARATOR` - Separator used between topic and timer ID (default: "--")

## Testing Approach

Tests focus on verifying:
- Handler registration and routing
- Timer scheduling and removal
- Payload validation with Pydantic
- Error handling for missing handlers
- Correct timer key construction

The test suite uses standard pytest patterns with async support.
