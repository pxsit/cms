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

"""Smoke tests of the admin web server (AWS).

The AWS pages are driven by jQuery and jqPlot, so these tests check that
they load and run without errors, and that a chart can be drawn.

"""

import subprocess

import pytest
from playwright.sync_api import expect

from cms import config as cms_config
from cmstestsuite.browser_tests import seed
from cmstestsuite.browser_tests.servers import executable, run_server

ADMIN = "browsertestadmin"
ADMIN_PASSWORD = "browsertestadmin-password"

# Most AWS pages talk to the other services (through RPC) to fill parts of
# themselves, and these are not running here, so some requests fail with
# server errors that the browser logs as console errors. Ignore those; the
# fixture in conftest.py still fails on uncaught exceptions and on any
# static file that is missing.
ALLOWED_CONSOLE_ERRORS = ["Failed to load resource"]


@pytest.fixture(scope="session")
def aws_url(seeded):
    """Start a real AWS on the seeded database and return its URL."""
    added = subprocess.run(
        [executable("cmsAddAdmin"), ADMIN, "-p", ADMIN_PASSWORD],
        capture_output=True, text=True)
    if added.returncode != 0:
        raise RuntimeError("cmsAddAdmin failed (%d): %s"
                           % (added.returncode, added.stderr[-1000:]))
    port = cms_config.admin_web_server.listen_port
    with run_server("cmsAdminWebServer", ["0"],
                    "http://127.0.0.1:%d/" % port) as url:
        yield url


@pytest.fixture
def admin_page(page, aws_url):
    page.goto(aws_url + "login")
    page.get_by_label("Username").fill(ADMIN)
    page.get_by_label("Password").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Login").click()
    try:
        page.wait_for_url(aws_url, wait_until="commit")
    except Exception:
        raise AssertionError("login failed: %s: %s" % (
            page.url, page.inner_text("body")[:300]))
    return page


# (path, a heading that only a correctly rendered page has)
PAGES = [
    ("", "Administration"),
    ("contests", "Administration"),
    ("contest/{c}", "Contest configuration"),
    ("contest/{c}/users", "Users list"),
    ("tasks", "Administration"),
    ("users", "Administration"),
    ("resources", "Administration"),
]


@pytest.mark.parametrize("path,heading", PAGES)
def test_pages_load(admin_page, aws_url, seeded, path, heading):
    admin_page.goto(aws_url + path.format(c=seeded.contest_id))
    expect(admin_page.get_by_role("heading", name=heading).first) \
        .to_be_visible()
    # jQuery 4 is the one that is loaded and it works.
    assert admin_page.evaluate(
        "typeof $ === 'function' && $.fn.jquery").startswith("4.")


def test_section_heading_hides_and_shows_its_section(
        admin_page, aws_url, seeded):
    # Section headings fold their section through click handlers that
    # base.html delegates from the document, one for the open state and
    # one for the folded state, so this needs several clicks.
    admin_page.goto(
        "%scontest/%d/announcements" % (aws_url, seeded.contest_id))
    heading = admin_page.get_by_role("heading", name="Announcements", level=2)
    announcement = admin_page.get_by_text(seed.ANNOUNCEMENT_SUBJECT)
    expect(announcement).to_be_visible()

    for _ in range(2):
        heading.click()
        expect(announcement).to_be_hidden()
        heading.click()
        expect(announcement).to_be_visible()


def test_resources_page_draws_a_chart(admin_page, aws_url):
    admin_page.goto(aws_url + "resources")
    # Draw a chart the way the page does, with the date axis and the
    # enhanced legend, to check that jqPlot works with this jQuery.
    admin_page.evaluate("""() => {
        const div = document.createElement('div');
        div.id = 'smoke_chart';
        div.style.width = '400px';
        div.style.height = '200px';
        document.body.appendChild(div);
        const now = Date.now();
        $.jqplot('smoke_chart', [[[now - 2000, 1], [now - 1000, 3], [now, 2]]], {
            axes: {xaxis: {renderer: $.jqplot.DateAxisRenderer}},
            legend: {show: true, renderer: $.jqplot.EnhancedLegendRenderer},
            series: [{label: 'Smoke'}],
        });
    }""")
    expect(admin_page.locator("#smoke_chart canvas").first).to_be_visible()
    expect(admin_page.locator("#smoke_chart")).to_contain_text("Smoke")
