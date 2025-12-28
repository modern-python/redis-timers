import os
import typing


TIMERS_TIMELINE_KEY: typing.Final = os.getenv("TIMERS_TIMELINE_KEY", "timers_timeline")
TIMERS_PAYLOADS_KEY: typing.Final = os.getenv("TIMERS_PAYLOADS_KEY", "timers_payloads")
TIMERS_HANDLING_SLEEP: float = float(os.getenv("TIMERS_HANDLING_SLEEP", "0.05"))
TIMERS_HANDLING_JITTER_MIN_VALUE: float = float(os.getenv("TIMERS_HANDLING_JITTER_MIN_VALUE", "0.5"))
TIMERS_HANDLING_JITTER_MAX_VALUE: float = float(os.getenv("TIMERS_HANDLING_JITTER_MAX_VALUE", "2.0"))
TIMERS_CONCURRENT_PROCESSING_LIMIT: int = int(os.getenv("TIMERS_CONCURRENT_PROCESSING_LIMIT", "5"))

TIMERS_SEPARATOR = "--"
