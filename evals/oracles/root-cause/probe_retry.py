"""Independent behavior oracle; does not establish the agent's diagnostic reasoning."""
from retrying import is_retryable, retry


class ServiceTimeout(TimeoutError):
    """The existing classifier includes TimeoutError subclasses."""


def check():
    for attempts in (1, 2, 4, 7):
        for error_type in (ValueError, RuntimeError, TimeoutError, ServiceTimeout):
            error = error_type("synthetic")
            calls = []

            def fail():
                calls.append(1)
                raise error

            try:
                retry(fail, max_attempts=attempts)
            except error_type as returned:
                assert returned is error, "exception identity lost"
            else:
                raise AssertionError("exception swallowed")
            retryable = issubclass(error_type, TimeoutError)
            expected = attempts if retryable else 1
            assert len(calls) == expected, (error_type, attempts, len(calls))
            assert is_retryable(error) is retryable
        for error_type in (TimeoutError, ServiceTimeout):
            for failures in range(attempts):
                calls = []
                value = object()

                def recover():
                    calls.append(1)
                    if len(calls) <= failures:
                        raise error_type("transient")
                    return value

                assert retry(recover, max_attempts=attempts) is value
                assert len(calls) == failures + 1


if __name__ == "__main__":
    check()
