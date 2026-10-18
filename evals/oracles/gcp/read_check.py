"""Hardened GCP case check: was a discriminating read set served within the read budget?

Usage: python -I -B _read_check.py READ_NAME[+READ_NAME ...] [READ_NAME[+READ_NAME ...] ...]
Each argument is one set of reads joined by '+'. The fixture appends each served read's name to
$HARNESS_STATE_DIR/reads-served.log; a read refused for budget is logged elsewhere and does not
count. Exit 0 when every read of any one set was served, 10 when none was. Standard library only.
"""

import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    groups = [set(arg.split('+')) for arg in argv]
    state = os.environ.get('HARNESS_STATE_DIR')
    if not groups or not all(groups) or not state:
        print('read check misconfigured: needs read sets and HARNESS_STATE_DIR')
        return 1
    log = Path(state) / 'reads-served.log'
    served = log.read_text(encoding='utf-8').split() if log.exists() else []
    hit = next((group for group in groups if group <= set(served)), None)
    if hit:
        print(f'discriminating read set served: {"+".join(sorted(hit))} (served reads: {", ".join(served)})')
        return 0
    print(f'no discriminating read set served (wanted any of {argv}; served: {", ".join(served) or "none"})')
    return 10


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
