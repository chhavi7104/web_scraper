"""Tiny local web server with fake company sites (used by tests and the demo)."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ACME = {
"/": """<html><head><title>Acme Cloud | Sovereign cloud for Europe</title>
<meta name="description" content="Acme Cloud is a leading European cloud computing provider offering sovereign IaaS and managed Kubernetes.">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Acme Cloud",
"foundingDate":"2016-03-01","address":{"@type":"PostalAddress","streetAddress":"Torstrasse 12",
"addressLocality":"Berlin","postalCode":"10119","addressCountry":"DE"}}</script>
<script src="/static/react.min.js"></script><script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>
<link rel="stylesheet" href="https://acme-assets.s3.amazonaws.com/site.css"></head>
<body><nav><a href="/about">About</a> <a href="/contact">Contact us</a> <a href="/products">Products</a>
<a href="/blog/roadmap">Blog</a> <a href="/files/brochure.pdf">Brochure</a> <a href="https://other.example.org/about">Partner</a></nav>
<h1>Cloud infrastructure you control</h1>
<p>We are the market leader in sovereign cloud computing for European startups. Our cloud platform runs on OpenStack and Kubernetes with PostgreSQL managed databases.</p>
<p>Looking for an alternative to Hetzner Cloud? Acme vs DigitalOcean: see how we compare. Cloud hosting, cloud storage and devops tooling.</p>
<footer><a href="https://www.linkedin.com/company/acme-cloud">LinkedIn</a> <a href="https://twitter.com/acmecloud">Twitter</a></footer></body></html>""",
"/about": """<html><head><title>About - Acme Cloud</title></head><body><h1>About us</h1>
<p>Acme Cloud was founded in 2016 in Berlin. We are currently building a sovereign object-storage service for regulated industries.</p></body></html>""",
"/contact": """<html><head><title>Contact - Acme Cloud</title></head><body><h1>Contact</h1>
<p>Email <a href="mailto:hello@acmecloud.eu?subject=Hi">hello@acmecloud.eu</a>, sales: sales@acmecloud.eu, noise: logo@2x.png</p>
<p>Call us on +49 30 1234 5678. Order #20240102 is not a phone.</p>
<address>Torstrasse 12, 10119 Berlin, Germany</address></body></html>""",
"/products": """<html><body><h2>Compute Instances</h2><h2>Managed Kubernetes</h2><h2>Object Storage</h2><h2>Subscribe to our newsletter</h2></body></html>""",
"/blog/roadmap": """<html><body><h1>Roadmap</h1><h2>Launching GPU instances in Frankfurt</h2><h2>Piloting carbon-aware scheduling</h2></body></html>""",
}
BARE = {"/": """<html><head><title>Bare Co</title></head><body><p>Hi. Mail us: info@bare.test</p></body></html>"""}
ROBOTS_BLOCKED = {"/": "<html><head><title>Hidden Inc</title></head><body>secret</body></html>",
                  "/robots.txt": "User-agent: *\nDisallow: /"}


def make_server(pages: dict, ctype: str = "text/html"):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = pages.get(self.path.split("?")[0])
            if body is None:
                self.send_response(404); self.end_headers(); return
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain" if self.path == "/robots.txt" else ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}/"
