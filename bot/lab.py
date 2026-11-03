"""Cloud lab entry point, started by pushing lab-request.txt (first line = command).

    probe                 check GDELT history range
    gdelt [minutes]       backfill/refresh GDELT news cache (default 100-minute budget)
    train                 full statistical training run (see bot/train.py)
"""
import sys


def main(argv=None):
    argv = argv or sys.argv[1:]
    cmd = argv[0] if argv else "probe"
    if cmd == "probe":
        from . import gdelt
        gdelt.probe()
    elif cmd == "gdelt":
        from . import gdelt
        gdelt.update(max_minutes=float(argv[1]) if len(argv) > 1 else 100)
    elif cmd == "train":
        from . import train
        train.main(argv[1:])
    else:
        raise SystemExit(f"unknown lab command {cmd}")


if __name__ == "__main__":
    main()
