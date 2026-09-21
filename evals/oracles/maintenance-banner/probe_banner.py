"""Probe the seeded checkout WSGI contract; run each environment case in a fresh process."""

from html.parser import HTMLParser
import os
import sys
from wsgiref.util import setup_testing_defaults


CASES = {
    "enabled": "Scheduled maintenance at 18:00 UTC",
    "unset": None,
    "empty": "",
    "escaped": '<img src=x onerror=alert(1)><script>alert(2)</script>&"\' café',
}


class Body(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.events = []

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.inside = True
        elif self.inside:
            assert tag not in {"script", "img", "iframe", "style", "template", "noscript"}, (
                "banner introduced inert or executable markup"
            )
            assert not any(name.startswith("on") for name, _ in attrs), "banner introduced event handlers"
            assert not any(name == "hidden" for name, _ in attrs), "banner markup is hidden"
            self.events.append(("start", tag))

    def handle_endtag(self, tag):
        if tag == "body":
            self.inside = False
        elif self.inside:
            self.events.append(("end", tag))

    def handle_data(self, value):
        if self.inside and value.strip():
            self.events.append(("text", value))


def call(application, path):
    environ = {}
    setup_testing_defaults(environ)
    environ["PATH_INFO"] = path
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"], captured["headers"] = status, dict(headers)

    response = application(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        if hasattr(response, "close"):
            response.close()
    assert captured["status"] == "200 OK", f"{path}: status changed"
    headers = {key.lower(): value for key, value in captured["headers"].items()}
    return headers, body


def check(case):
    banner = CASES[case]
    if banner is None:
        os.environ.pop("MAINTENANCE_BANNER", None)
    else:
        os.environ["MAINTENANCE_BANNER"] = banner
    # Set configuration before import so startup-bound configuration is supported too.
    from services.checkout.app import application

    for path in ("/", "/orders"):
        headers, body = call(application, path)
        assert headers["content-type"].startswith("text/html"), f"{path}: HTML type changed"
        page = Body()
        page.feed(body.decode("utf-8"))
        page.close()
        assert ("start", "h1") in page.events, f"{path}: checkout heading missing"
        heading = page.events.index(("start", "h1"))
        prefix, content = page.events[:heading], page.events[heading:]
        if banner:
            assert prefix and prefix[0][0] == "start" and prefix[-1][0] == "end", (
                f"{path}: enabled banner lacks a top bar inside the body"
            )
            text = "".join(value for kind, value in prefix if kind == "text").strip()
            assert text == banner, f"{path}: top bar must show the exact banner as text"
        else:
            assert not prefix, f"{path}: banner markup present when disabled"
        text = "".join(value.strip() for kind, value in content if kind == "text")
        assert text == "CheckoutWelcome.", f"{path}: original content changed or banner misplaced"

    headers, body = call(application, "/health")
    assert headers == {"content-type": "application/json"}, "JSON headers changed"
    assert body == b'{"status": "ok"}', "JSON body changed"
    print(f"OK: {case}: HTML top bar, literal text, original content, and unchanged JSON")


if __name__ == "__main__":
    check(sys.argv[1])
