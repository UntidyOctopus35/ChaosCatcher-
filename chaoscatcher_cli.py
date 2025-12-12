#!/usr/bin/env python3
"""
Thin wrapper so you can run:

    python chaoscatcher_cli.py summary
    python chaoscatcher_cli.py water status
    python chaoscatcher_cli.py vyvanse status

while keeping all the real logic inside chaoscatcher.py.
"""

import sys
from typing import Optional, List

import chaoscatcher  # this is your main CLI implementation


def main(argv: Optional[List[str]] = None) -> None:
    """
    Delegate to chaoscatcher.main so we don't duplicate logic.
    """
    if argv is None:
        argv = sys.argv[1:]

    chaoscatcher.main(argv)


if __name__ == "__main__":
    main()
