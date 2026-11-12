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

"""Browser tests for the testing page: the list of tests, downloads and the
form. Its tabs, details dialog and download menus are tested with the
other Bootstrap behaviours in bootstrap_js_test.py."""

import pytest
from playwright.sync_api import expect

from cmstestsuite.browser_tests import seed


@pytest.fixture
def testing(page, base_url, login):
    login(seed.READER)
    page.goto(base_url + "testing")
    return page


def test_previous_tests_are_listed(testing):
    rows = testing.locator("#test_%s tr[data-user-test]" % seed.TASK_NAME)
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Executed")


def test_single_file_test_has_a_direct_download_link(testing):
    pane = testing.locator("#test_%s" % seed.TASK_NAME)
    link = pane.locator("tr[data-user-test] td.files") \
        .get_by_role("link", name="Download")
    with testing.expect_download() as info:
        link.click()
    assert info.value.suggested_filename == "sum.py"


def test_submit_test_form_has_file_inputs_and_language(testing):
    pane = testing.locator("#test_%s" % seed.TASK_NAME)
    expect(pane.get_by_role("heading", name="Submit a test")).to_be_visible()
    expect(pane.locator("input[type=file][name='sum.%l']")).to_be_visible()
    expect(pane.locator("input[type=file][name=input]")).to_be_visible()
    expect(pane.locator("select[name=language]")).to_be_visible()
