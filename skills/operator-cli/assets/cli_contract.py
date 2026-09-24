"""Cancel stale open orders: the reference command for the operator-cli contract.

Adapt the selection, the effect client, and the flags; keep the contract: a dry run with zero
effects, confirmation only from a terminal or --yes, one outcome per item, exit codes
0/1/2/130/143, cleanup on SIGINT and SIGTERM, and a quiet exit when stdout closes early.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import signal
import stat
import sys
from pathlib import Path
from uuid import uuid4

import orders_client  # effect seam: list_stale(minutes), cancel(order_id), status(order_id), OrderError

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2
LOCK = Path("cancel_stale_orders.lock")


class Stopped(BaseException):
    """SIGINT or SIGTERM arrived; unwind through cleanup, then exit 128 + signum.

    A BaseException, like KeyboardInterrupt, so no `except Exception` swallows it.
    """

    def __init__(self, signum: int) -> None:
        super().__init__(signum)
        self.signum = signum


def _stop(signum, frame):
    signal.signal(signum, signal.SIG_DFL)  # a second signal skips slow cleanup
    raise Stopped(signum)


@contextmanager
def defer_stop():
    """Finish a short local lock transition before unwinding; a second signal still stops now."""
    pending = []

    def defer(signum, frame):
        pending.append(signum)
        signal.signal(signum, signal.SIG_DFL)

    previous = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        if signal.getsignal(signum) is _stop:
            previous[signum] = signal.signal(signum, defer)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            if signum not in pending:
                signal.signal(signum, handler)
        if pending:
            raise Stopped(pending[0])


@contextmanager
def owned_lock():
    """Exclusive cooperative lock; never remove a file another run put in its place."""
    owner = f"{os.getpid()}:{uuid4().hex}"
    identity = None
    written = False

    def check_owner():
        current = LOCK.lstat()
        if (not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity
                or (written and LOCK.read_text(encoding="utf-8") != owner)):
            raise OSError(f"{LOCK}: ownership changed; stop and inspect the lock before re-running")

    try:
        with defer_stop():
            with LOCK.open("x", encoding="utf-8") as stream:
                info = os.fstat(stream.fileno())
                identity = (info.st_dev, info.st_ino)
                stream.write(owner)
                stream.flush()
                written = True
        yield check_owner
    finally:
        if identity is not None:
            interrupted = isinstance(sys.exc_info()[1], Stopped)
            try:
                with defer_stop():
                    check_owner()
                    LOCK.unlink()
            except OSError as exc:
                if not interrupted:
                    raise
                print(f"error: cleanup: {exc}", file=sys.stderr)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cancel open orders older than a threshold.",
        epilog="Exit codes: 0 all cancelled or dry run; 1 an order failed or is unknown; "
               "2 usage or missing confirmation; 130/143 interrupted. "
               "Example: cancel_stale_orders --older-than 30 --dry-run",
    )
    parser.add_argument("--older-than", type=positive_int, default=30, metavar="MINUTES",
                        help="age threshold greater than zero (default: 30 minutes)")
    parser.add_argument("--max-items", type=positive_int, default=100,
                        help="refuse plans above this positive cap (default: 100); stop on the first failed or unknown item")
    parser.add_argument("--dry-run", action="store_true", help="show the orders; cancel nothing")
    parser.add_argument("--yes", action="store_true", help="confirm without a prompt")
    parser.add_argument("--no-input", action="store_true", help="never prompt")
    parser.add_argument("--json", action="store_true", help="print one JSON object on stdout")
    return parser.parse_args(argv)


def cancel_one(order_id: str) -> str:
    try:
        orders_client.cancel(order_id)
        return "succeeded"
    except orders_client.OrderError as exc:
        print(f"error: {order_id}: {exc}", file=sys.stderr)
        return "failed"
    except TimeoutError:
        try:  # the cancel may have happened: read back before classifying it
            return "succeeded" if orders_client.status(order_id) == "cancelled" else "unknown"
        except Exception:
            return "unknown"


def report(items: list[dict], args: argparse.Namespace) -> None:
    if args.json:
        print(json.dumps({"items": items}))
    else:
        for item in items:
            print(f"{item['id']}\t{item['status']}")
    sys.stdout.flush()


def run(args: argparse.Namespace) -> int:
    plan = sorted(set(orders_client.list_stale(args.older_than)))
    items = [{"id": order_id, "status": "skipped"} for order_id in plan]
    if len(plan) > args.max_items:
        print(f"error: {len(plan)} orders exceeds --max-items {args.max_items}; narrow the selection or review a larger cap",
              file=sys.stderr)
        report(items, args)
        return EXIT_FAILED
    if args.dry_run:
        report(items, args)
        return EXIT_OK
    if not args.yes:
        if args.no_input or not sys.stdin.isatty():
            print("error: confirmation required: pass --yes or run on a terminal", file=sys.stderr)
            return EXIT_USAGE
        print("\n".join(plan), file=sys.stderr)
        print(f"Cancel these {len(plan)} orders? [y/N] ", end="", file=sys.stderr, flush=True)
        if input().strip().lower() != "y":
            return EXIT_USAGE
    code = EXIT_OK
    try:
        with owned_lock() as check_owner:
            if sorted(set(orders_client.list_stale(args.older_than))) != plan:
                print("error: the stale set changed after selection; re-run to review it", file=sys.stderr)
                code = EXIT_FAILED
            else:
                for item in items:
                    check_owner()
                    item["status"] = "unknown"  # in flight until the call returns
                    item["status"] = cancel_one(item["id"])
                    if item["status"] != "succeeded":
                        code = EXIT_FAILED
                        break
    except Stopped as stop:
        code = 128 + stop.signum
    except FileExistsError:
        print(f"error: {LOCK} already exists; check the owning run before retrying", file=sys.stderr)
        code = EXIT_FAILED
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        code = EXIT_FAILED
    report(items, args)
    return code


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    try:
        return run(args)
    except Stopped as stop:
        return 128 + stop.signum
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)  # Python flushes stdout again at exit
        os.dup2(devnull, sys.stdout.fileno())
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
