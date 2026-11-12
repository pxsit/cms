#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2026 Pasit Sangprachathanarak <ouipingpasit@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Fixtures for the browser tests of the contest web server (CWS).

The tests need Playwright and its browser, a PostgreSQL database whose
name ends in "fortesting", and a CMS_CONFIG pointing to it. They are run
with:

    pip install -c constraints.txt -r constraints-browser-test.txt
    playwright install chromium
    pytest cmstestsuite/browser_tests

"""

import os

import pytest

pytest.importorskip(
    "playwright", reason="run 'pip install -c constraints.txt -r "
    "constraints-browser-test.txt' to run these tests")

from cms import config as cms_config  # noqa: E402
from cmstestsuite.browser_tests import seed  # noqa: E402
from cmstestsuite.browser_tests.servers import run_server  # noqa: E402


def pytest_collection_modifyitems(items):
    here = os.path.dirname(__file__)
    for item in items:
        if str(item.fspath).startswith(here):
            item.add_marker(pytest.mark.browser)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "browser: drives a real browser against a running CWS")
    config.addinivalue_line(
        "markers",
        "allow_browser_errors: do not fail on console errors, page errors "
        "or failed static assets")


@pytest.fixture(scope="session")
def seeded():
    """Recreate the test database and fill it with the fixtures."""
    return seed.seed_database()


@pytest.fixture(scope="session")
def base_url(seeded):
    """Start a real CWS on the seeded contest, and return its URL.

    Only the CWS runs: the seeded submissions are already evaluated, so
    no worker or evaluation service is needed.

    """
    port = cms_config.contest_web_server.listen_port[0]
    with run_server("cmsContestWebServer",
                    ["0", "-c", str(seeded.contest_id)],
                    "http://127.0.0.1:%d/" % port) as url:
        yield url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 900},
        "locale": "en-US",
    }


# Console messages that are known to be noise rather than regressions.
# Keep this list short and explain each entry. A test module can add its
# own entries with a module-level ALLOWED_CONSOLE_ERRORS list.
ALLOWED_CONSOLE_ERRORS: list[str] = []


@pytest.fixture(autouse=True)
def fail_on_browser_errors(request, page):
    """Fail a test on console errors, page errors or broken static files.

    This catches broken JavaScript and missing CSS/JS assets, which are
    the typical symptom of a front-end framework migration gone wrong.

    """
    problems: list[str] = []
    allowed = ALLOWED_CONSOLE_ERRORS + getattr(
        request.module, "ALLOWED_CONSOLE_ERRORS", [])

    def on_console(msg):
        if msg.type == "error" and not any(
                a in msg.text for a in allowed):
            problems.append("console error: %s" % msg.text)

    def on_page_error(exc):
        problems.append("uncaught exception: %s" % exc)

    def on_response(response):
        if "/static/" in response.url and response.status >= 400:
            problems.append(
                "static asset %s returned %d" % (response.url, response.status))

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("response", on_response)
    yield
    if request.node.get_closest_marker("allow_browser_errors") is None:
        assert not problems, "\n".join(problems)


@pytest.fixture
def login(page, base_url, seeded):
    """Return a function logging a seeded user in to the contest."""
    def do_login(username: str):
        page.goto(base_url)
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill(seed.PASSWORDS[username])
        page.get_by_role("button", name="Login").click()
        page.get_by_role("button", name="Logout").wait_for()
    return do_login
