"""Convert between the three storage revisions and the fully expanded JSON format."""
import argparse
import json
from pathlib import Path
import os
from tempfile import NamedTemporaryFile

from storage import compact, expand, to_round_one, to_round_two


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compact", "expand", "to-r1", "to-r2"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_bytes())
    transform = {"compact": compact, "expand": expand, "to-r1": to_round_one, "to-r2": to_round_two}[args.command]
    result = transform(source)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    temp = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.destination.parent, delete=False) as file:
            temp = Path(file.name)
            file.write(text)
        os.replace(temp, args.destination)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
