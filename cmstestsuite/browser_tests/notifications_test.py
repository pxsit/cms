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

"""Browser tests for the alerts that CWS builds in JavaScript when there
is something new (announcement, message, answer). Showing and dismissing
them is tested in bootstrap_js_test.py."""

from playwright.sync_api import expect

from cmstestsuite.browser_tests import seed


def test_user_without_news_sees_only_the_announcement(page, base_url, login):
    login(seed.NOBODY)
    expect(page.locator("#notifications > *")).to_have_count(1)
