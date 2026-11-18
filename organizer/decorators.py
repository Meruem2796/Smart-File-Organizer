import functools
import logging
import sys
import time

logger = logging.getLogger(__name__)


def log_operation(func):
    @functools.wraps(func)  # keeps the original name and docstring
    def wrapper(*args, **kwargs):  # *args, **kwargs = accept any arguments
        try:
            result = func(*args, **kwargs)
        except (
            Exception
        ) as error:  # Ctrl+C is not an Exception, so it passes through
            # a full traceback only when debug logging is on (main.py -v)
            logger.error(
                "%s failed: %s",
                func.__name__,
                error,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            raise  # log it, but do not hide it
        logger.info("%s succeeded", func.__name__)
        return result

    return wrapper


def measure_execution_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:  # runs on success AND on failure
            elapsed = time.perf_counter() - start
            print(
                f"{func.__name__} took {elapsed:.4f} seconds", file=sys.stderr
            )

    return wrapper
