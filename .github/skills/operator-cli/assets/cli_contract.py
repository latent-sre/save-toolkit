"""Cancel stale open orders: the reference command for the operator-cli contract.

Adapt the selection, the effect client, and the flags; keep the contract: a dry run with zero
effects, confirmation only from a terminal or --yes, one outcome per item, exit codes
0/1/2/130/143, cleanup on SIGINT and SIGTERM, and a quiet exit when stdout closes early.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from pathlib import Path

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


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cancel open orders older than a threshold.",
        epilog="Exit codes: 0 all cancelled or dry run; 1 an order failed or is unknown; "
               "2 usage or missing confirmation; 130/143 interrupted. "
               "Example: cancel_stale_orders --older-than 30 --dry-run",
    )
    parser.add_argument("--older-than", type=int, default=30, metavar="MINUTES")
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
    plan = orders_client.list_stale(args.older_than)
    if args.dry_run:
        if args.json:
            print(json.dumps({"plan": plan}))
        else:
            print("\n".join(plan))
        sys.stdout.flush()
        return EXIT_OK
    if not args.yes:
        if args.no_input or not sys.stdin.isatty():
            print("error: confirmation required: pass --yes or run on a terminal", file=sys.stderr)
            return EXIT_USAGE
        print("\n".join(plan), file=sys.stderr)
        if input(f"Cancel these {len(plan)} orders? [y/N] ").strip().lower() != "y":
            return EXIT_USAGE
        if orders_client.list_stale(args.older_than) != plan:
            print("error: the stale set changed after it was shown; re-run to review it", file=sys.stderr)
            return EXIT_FAILED
    items = [{"id": order_id, "status": "skipped"} for order_id in plan]
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    try:
        for item in items:
            item["status"] = "unknown"  # in flight until the call returns
            item["status"] = cancel_one(item["id"])
    except Stopped as stop:
        report(items, args)
        return 128 + stop.signum
    finally:
        LOCK.unlink(missing_ok=True)
    report(items, args)
    return EXIT_OK if all(item["status"] == "succeeded" for item in items) else EXIT_FAILED


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
