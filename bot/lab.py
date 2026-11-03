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
    elif cmd == "gdelt-part":      # gdelt-part <i> <n> [minutes]: only series i, i+n, i+2n... missing from cache
        from . import gdelt
        i, n = int(argv[1]), int(argv[2])
        allk = list(gdelt.COMPANY_QUERIES) + list(gdelt.WORLD_QUERIES)
        todo = [k for k in allk if not (gdelt.CACHE / f"{k.replace('&', 'and')}.csv").exists()]
        mine = todo[i::n]
        print(f"[lab] part {i}/{n}: {len(mine)} series: {', '.join(mine)}")
        gdelt.update(keys=mine, max_minutes=float(argv[3]) if len(argv) > 3 else 130)
    elif cmd == "gdelt-vol-part":  # gdelt-vol-part <i> <n>: re-download attention for every i-th series
        from . import gdelt
        i, n = int(argv[1]), int(argv[2])
        allk = list(gdelt.COMPANY_QUERIES) + list(gdelt.WORLD_QUERIES)
        gdelt.redownload_vol(allk[i::n])
        missing = [k for k in allk[i::n] if not (gdelt.CACHE / f"{k.replace('&', 'and')}.csv").exists()]
        if missing:
            gdelt.update(keys=missing, max_minutes=60)
    elif cmd == "train":
        from . import train
        train.main(argv[1:])
    else:
        raise SystemExit(f"unknown lab command {cmd}")


if __name__ == "__main__":
    main()
