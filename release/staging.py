"""Fail closed when an interrupted upload does not match one original artifact set."""
import argparse
from pathlib import Path


def same_asset_recovery(existing, original):
    for path in existing.iterdir():
        if not path.is_file() or not (original / path.name).is_file():
            raise ValueError("Unexpected existing release asset: " + path.name)
        if path.read_bytes() != (original / path.name).read_bytes():
            raise ValueError("Existing release asset differs: " + path.name +
                             ". Recover from the original CI artifact set; do not mix builds.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("existing", type=Path)
    parser.add_argument("original", type=Path)
    args = parser.parse_args()
    try:
        same_asset_recovery(args.existing, args.original)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
