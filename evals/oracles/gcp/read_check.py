"""Hardened GCP case check: was a discriminating read served within the read budget?

Usage: python -I -B _read_check.py READ_NAME [READ_NAME ...]
The fixture appends each served read's name to $HARNESS_STATE_DIR/reads-served.log; a read refused
for budget is logged elsewhere and does not count. Exit 0 when any named read was served, 1 when
none was. Standard library only.
"""

import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    wanted = set(argv)
    state = os.environ.get('HARNESS_STATE_DIR')
    if not wanted or not state:
        print('read check misconfigured: needs read names and HARNESS_STATE_DIR')
        return 1
    log = Path(state) / 'reads-served.log'
    served = log.read_text(encoding='utf-8').split() if log.exists() else []
    hit = [name for name in served if name in wanted]
    if hit:
        print(f'discriminating read served: {hit[0]} (served reads: {", ".join(served)})')
        return 0
    print(f'no discriminating read served (wanted any of {sorted(wanted)}; served: {", ".join(served) or "none"})')
    return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
