"""Offline demo: serves fake company sites locally and runs the real CLI against them.

    python demo.py        # writes sample_output/companies.{json,csv}
"""
import sys
sys.path.insert(0, "tests")
import fixtures
from scraper.cli import main

a, acme = fixtures.make_server(fixtures.ACME)
b, bare = fixtures.make_server(fixtures.BARE)
sys.exit(main(["-u", acme, bare, "http://127.0.0.1:9/", "not a url", "--delay", "0",
               "--timeout", "3", "-o", "sample_output/companies", "--log-file", "sample_output/scraper.log"]))
