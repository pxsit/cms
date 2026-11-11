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

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import expect

from cms import config as cms_config

ADMIN = "browsertestadmin"
ADMIN_PASSWORD = "browsertestadmin-password"


@pytest.fixture(scope="session")
def aws_url(seeded):
    """Start a real AWS on the seeded database and return its URL."""
    subprocess.run(
        [os.path.join(sys.prefix, "bin", "cmsAddAdmin"), ADMIN,
         "-p", ADMIN_PASSWORD],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    port = cms_config.admin_web_server.listen_port
    url = "http://127.0.0.1:%d/" % port
    executable = os.path.join(sys.prefix, "bin", "cmsAdminWebServer")
    verbose = os.environ.get("CMS_BROWSER_TEST_VERBOSE")
    proc = subprocess.Popen(
        [executable, "0"],
        stdout=None if verbose else subprocess.DEVNULL,
        stderr=None if verbose else subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 60
        while True:
            if proc.poll() is not None:
                raise RuntimeError(
                    "AdminWebServer exited early with code %s "
                    "(set CMS_BROWSER_TEST_VERBOSE=1 to see its output)"
                    % proc.returncode)
            try:
                urllib.request.urlopen(url, timeout=2).close()
                break
            except urllib.error.HTTPError:
                break
            except (urllib.error.URLError, OSError):
                if time.monotonic() > deadline:
                    raise RuntimeError("AdminWebServer did not come up")
                time.sleep(0.3)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# Most AWS pages talk to the other services (through RPC) to fill parts of
# themselves, and these are not running here, so some requests fail with
# server errors. These tests do not care about that: they check that the
# pages load and that their JavaScript, which needs jQuery and jqPlot, runs
# without uncaught exceptions.
pytestmark = pytest.mark.allow_browser_errors


@pytest.fixture
def js_errors(page):
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    yield errors
    assert not errors, "uncaught exceptions: %s" % errors


@pytest.fixture
def admin_page(page, aws_url, js_errors):
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


@pytest.mark.parametrize("path", [
    "", "contests", "contest/{c}", "contest/{c}/users", "tasks", "users",
    "resources"])
def test_pages_load(admin_page, aws_url, seeded, path):
    admin_page.goto(aws_url + path.format(c=seeded.contest_id))
    expect(admin_page.locator("#nav_sidebar, nav, .sidebar, body").first)         .to_be_visible()
    # jQuery is there and working.
    assert admin_page.evaluate("typeof $ === 'function' && $.fn.jquery")         .startswith("4.")


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
