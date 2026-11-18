import contextlib
import io
import unittest

from organizer.decorators import log_operation, measure_execution_time


class TestLogOperation(unittest.TestCase):
    def test_keeps_name_and_docstring(self):
        @log_operation
        def my_function():
            """My docs."""

        self.assertEqual(my_function.__name__, "my_function")
        self.assertEqual(my_function.__doc__, "My docs.")

    def test_returns_result_and_logs_success(self):
        @log_operation
        def add(a, b=0):
            return a + b

        with self.assertLogs("organizer.decorators", level="INFO") as logs:
            self.assertEqual(add(2, b=3), 5)
        self.assertEqual(
            logs.output, ["INFO:organizer.decorators:add succeeded"]
        )

    def test_logs_failure_and_reraises_same_error(self):
        error = ValueError("boom")

        @log_operation
        def explode():
            raise error

        with self.assertLogs("organizer.decorators", level="INFO") as logs:
            with self.assertRaises(ValueError) as caught:
                explode()
        self.assertIs(caught.exception, error)
        self.assertEqual(
            logs.output, ["ERROR:organizer.decorators:explode failed: boom"]
        )

    def test_traceback_is_attached_only_at_debug_level(self):
        @log_operation
        def explode():
            raise ValueError("boom")

        with self.assertLogs("organizer.decorators", level="DEBUG") as logs:
            with self.assertRaises(ValueError):
                explode()
        self.assertIn("Traceback", logs.output[0])


class TestMeasureExecutionTime(unittest.TestCase):
    def test_keeps_name_and_docstring(self):
        @measure_execution_time
        def my_function():
            """My docs."""

        self.assertEqual(my_function.__name__, "my_function")
        self.assertEqual(my_function.__doc__, "My docs.")

    def test_returns_result_and_prints_time_to_stderr(self):
        @measure_execution_time
        def double(x):
            return x * 2

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(double(4), 8)
        self.assertRegex(err.getvalue(), r"^double took \d+\.\d{4} seconds\n$")

    def test_prints_nothing_to_stdout(self):
        @measure_execution_time
        def nothing():
            return None

        out = io.StringIO()
        with (
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            nothing()
        self.assertEqual(out.getvalue(), "")

    def test_still_prints_time_when_function_fails(self):
        @measure_execution_time
        def explode():
            raise RuntimeError("boom")

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(RuntimeError):
                explode()
        self.assertIn("explode took", err.getvalue())


class TestStacking(unittest.TestCase):
    def test_stacked_decorators_both_apply_and_errors_propagate(self):
        @log_operation  # outer: sees the result or the error
        @measure_execution_time  # inner: closest to def, wraps first
        def work(value):
            if value < 0:
                raise ValueError("negative")
            return value

        err = io.StringIO()
        with (
            contextlib.redirect_stderr(err),
            self.assertLogs("organizer.decorators", level="INFO") as logs,
        ):
            self.assertEqual(work(3), 3)
            with self.assertRaises(ValueError):
                work(-1)
        self.assertEqual(
            err.getvalue().count("work took"), 2
        )  # timed even the failing call
        self.assertEqual(
            [line.split(":")[0] for line in logs.output], ["INFO", "ERROR"]
        )
        self.assertEqual(work.__name__, "work")


if __name__ == "__main__":
    unittest.main()
