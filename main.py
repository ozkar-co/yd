#!/usr/bin/env python3
"""yd — entrypoint REPL."""

from __future__ import annotations

import sys

from repl import main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nabort", file=sys.stderr)
        raise SystemExit(130) from None
