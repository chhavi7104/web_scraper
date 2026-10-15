"""Command-line interface."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .fetcher import Fetcher
from .output import write_csv, write_json
from .pipeline import Config, run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m scraper",
                                description="Discover companies and extract structured details.")
    src = p.add_argument_group("input (at least one)")
    src.add_argument("-q", "--query", help='search query, e.g. "cloud computing startups in Europe"')
    src.add_argument("-u", "--urls", nargs="+", default=[], help="seed company URLs / domains")
    src.add_argument("-f", "--urls-file", help="text file with one URL per line")
    o = p.add_argument_group("options")
    o.add_argument("-l", "--level", type=int, choices=(1, 2, 3), default=3,
                   help="1=basic, 2=+enhanced details, 3=+tech/projects/competitors (default 3)")
    o.add_argument("-n", "--max-companies", type=int, default=10)
    o.add_argument("--max-pages", type=int, default=6, help="max pages crawled per company")
    o.add_argument("--delay", type=float, default=1.0, help="seconds between requests to one host")
    o.add_argument("--timeout", type=float, default=10.0)
    o.add_argument("--proxy", help="HTTP(S) proxy URL")
    o.add_argument("--ignore-robots", action="store_true", help="do not honour robots.txt (not recommended)")
    o.add_argument("--format", choices=("json", "csv", "both"), default="both")
    o.add_argument("-o", "--output", default="output/companies", help="output path without extension")
    o.add_argument("--log-file", default="scraper.log")
    o.add_argument("-v", "--verbose", action="store_true")
    return p


def setup_logging(log_file: str, verbose: bool) -> None:
    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    handlers = [logging.StreamHandler(sys.stderr)]
    handlers[0].setLevel(logging.DEBUG if verbose else logging.WARNING)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG, format=fmt, handlers=handlers + [fh])
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    urls = list(args.urls)
    if args.urls_file:
        try:
            lines = Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        except OSError as e:
            print(f"error: cannot read {args.urls_file}: {e}", file=sys.stderr)
            return 2
        urls += [l.strip() for l in lines if l.strip() and not l.startswith("#")]
    if not args.query and not urls:
        print("error: provide --query and/or --urls/--urls-file", file=sys.stderr)
        return 2

    setup_logging(args.log_file, args.verbose)
    proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
    fetcher = Fetcher(delay=args.delay, timeout=args.timeout, respect_robots=not args.ignore_robots,
                      proxies=proxies)
    cfg = Config(args.max_companies, args.max_pages, args.level)

    def progress(i, n, url):
        print(f"[{i}/{n}] {url}", file=sys.stderr)

    companies, failures = run(args.query, urls, fetcher, cfg, progress=progress)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.format in ("json", "both"):
        write_json(companies, failures, str(out) + ".json", args.level)
    if args.format in ("csv", "both"):
        write_csv(companies, str(out) + ".csv", args.level)

    print(f"\nDone: {len(companies)} scraped, {len(failures)} failed. Output: {out}.*", file=sys.stderr)
    for f in failures:
        print(f"  FAILED {f['input']}: {f['error']}", file=sys.stderr)
    return 0 if companies else 1
