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

"""Browser tests for the behaviours CWS gets from the Bootstrap
JavaScript plugins: modals, dropdowns, tabs and dismissable alerts.

They are a regression gate for changing the version of Bootstrap, so they
must not depend on it: elements are found by role, label, text or by the
ids and data attributes of CWS itself, never by Bootstrap class names or
data-toggle / data-dismiss attributes, and "open" and "closed" are checked
with visibility assertions.

"""

import pytest
from playwright.sync_api import expect

from cmstestsuite.browser_tests import seed


def tab(page, name):
    """Find a tab trigger. Depending on the Bootstrap version it is exposed
    as a link or as a tab."""
    return page.get_by_role("tab", name=name, exact=True).or_(
        page.get_by_role("link", name=name, exact=True))


def open_page(page, base_url, kind, task):
    """Open the submissions or the testing page, showing the given task."""
    if kind == "submissions":
        page.goto("%stasks/%s/submissions" % (base_url, task))
    else:
        page.goto(base_url + "testing")
        tab(page, task).click()


def page_body_click(page):
    """Click on something inert, outside of any menu or dialog."""
    page.get_by_role("heading").first.click()


# Modals.
#
# Both pages have a dialog whose body is loaded with an AJAX request when
# it is opened, and that can be closed with the "x" in its header (whose
# accessible name is "Close") or with the "Close" in its footer (whose
# text is "Close").


MODALS = [
    pytest.param(
        "submissions", "submission_detail", "Submission details",
        "Output is correct", id="submission"),
    pytest.param(
        "testing", "user_test_detail", "Test details",
        "Execution completed successfully", id="user_test"),
]


@pytest.fixture
def modal_page(page, base_url, login):
    login(seed.READER)
    return page


def open_modal(page, base_url, section, dialog_id, title, content):
    open_page(page, base_url, section, seed.TASK_NAME)
    dialog = page.locator("#" + dialog_id)
    heading = dialog.get_by_role("heading", name=title)
    expect(heading).to_be_hidden()

    with page.expect_response(
            lambda r: r.url.endswith("/details") and r.status == 200):
        page.get_by_text("details", exact=True).first.click()
    expect(heading).to_be_visible()
    # The content comes from the AJAX request, after a loading message.
    expect(dialog.get_by_text(content)).to_be_visible()
    expect(dialog.get_by_text("loading...")).to_have_count(0)
    return dialog, heading


@pytest.mark.parametrize("section,dialog_id,title,content", MODALS)
def test_modal_opens_with_loaded_content(
        modal_page, base_url, section, dialog_id, title, content):
    open_modal(modal_page, base_url, section, dialog_id, title, content)


@pytest.mark.parametrize("section,dialog_id,title,content", MODALS)
def test_modal_closes_with_the_header_button(
        modal_page, base_url, section, dialog_id, title, content):
    dialog, heading = open_modal(
        modal_page, base_url, section, dialog_id, title, content)
    dialog.get_by_label("Close").click()
    expect(heading).to_be_hidden()
    expect(dialog.get_by_text(content)).to_be_hidden()


@pytest.mark.parametrize("section,dialog_id,title,content", MODALS)
def test_modal_closes_with_the_footer_button(
        modal_page, base_url, section, dialog_id, title, content):
    dialog, heading = open_modal(
        modal_page, base_url, section, dialog_id, title, content)
    dialog.get_by_text("Close", exact=True).click()
    expect(heading).to_be_hidden()
    expect(dialog.get_by_text(content)).to_be_hidden()


@pytest.mark.parametrize("section,dialog_id,title,content", MODALS)
def test_modal_can_be_reopened_and_leaves_the_page_usable(
        modal_page, base_url, section, dialog_id, title, content):
    page = modal_page
    dialog, heading = open_modal(
        page, base_url, section, dialog_id, title, content)
    dialog.get_by_text("Close", exact=True).click()
    expect(heading).to_be_hidden()

    # Nothing (such as a leftover backdrop) covers the page, so that the
    # link opening the dialog can be clicked again.
    page.get_by_text("details", exact=True).first.click()
    expect(heading).to_be_visible()
    expect(dialog.get_by_text(content)).to_be_visible()
    dialog.get_by_label("Close").click()
    expect(heading).to_be_hidden()


# Dropdowns.
#
# A task with several files has a "Download" menu instead of a link, both
# in the list of submissions and in the list of tests.


@pytest.fixture
def menu(page, base_url, login, request):
    """The toggle and the entries of the download menu of a pair task."""
    section, row_selector = request.param
    login(seed.READER)
    open_page(page, base_url, section, seed.PAIR_TASK_NAME)
    row = page.locator(row_selector)
    expect(row).to_have_count(1)
    toggle = row.get_by_text("Download", exact=True)
    entries = [row.get_by_role("link", name=name)
               for name in seed.PAIR_FILES]
    return toggle, entries


@pytest.mark.parametrize(
    "menu", [("submissions", "tr[data-submission]"),
             ("testing", "#test_pair tr[data-user-test] td.files")],
    indirect=True, ids=["submission", "user_test"])
class TestDropdown:

    def test_closed_until_clicked(self, menu):
        toggle, entries = menu
        expect(toggle).to_be_visible()
        for entry in entries:
            expect(entry).to_be_hidden()

    def test_click_opens_the_menu(self, menu):
        toggle, entries = menu
        toggle.click()
        for entry in entries:
            expect(entry).to_be_visible()

    def test_click_outside_closes_the_menu(self, page, menu):
        toggle, entries = menu
        toggle.click()
        expect(entries[0]).to_be_visible()
        page_body_click(page)
        for entry in entries:
            expect(entry).to_be_hidden()

    def test_second_click_closes_the_menu(self, menu):
        toggle, entries = menu
        toggle.click()
        expect(entries[0]).to_be_visible()
        toggle.click()
        for entry in entries:
            expect(entry).to_be_hidden()

    def test_menu_can_be_opened_again(self, page, menu):
        toggle, entries = menu
        toggle.click()
        page_body_click(page)
        expect(entries[0]).to_be_hidden()
        toggle.click()
        for entry in entries:
            expect(entry).to_be_visible()

    def test_entries_download_the_files(self, page, menu):
        toggle, entries = menu
        toggle.click()
        with page.expect_download() as info:
            entries[1].click()
        assert info.value.suggested_filename == seed.PAIR_FILES[1]


# Tabs.


def test_registration_tabs_show_the_matching_form(page, base_url):
    page.goto(base_url + "register")
    first_name = page.get_by_label("First name")
    confirm = page.get_by_label("Confirm password")
    new_user = tab(page, "New user")
    join = tab(page, "Join contest")

    # "New user" is selected first, and asks for the whole profile.
    expect(first_name).to_be_visible()
    expect(confirm).to_be_visible()

    join.click()
    expect(first_name).to_be_hidden()
    expect(confirm).to_be_hidden()
    # What both forms need stays visible.
    expect(page.get_by_label("Username")).to_be_visible()
    expect(page.get_by_label("Password", exact=True)).to_be_visible()

    new_user.click()
    expect(first_name).to_be_visible()
    expect(confirm).to_be_visible()

    # Selecting the tab already selected changes nothing.
    new_user.click()
    expect(first_name).to_be_visible()
    expect(confirm).to_be_visible()


def test_testing_tabs_show_one_task_at_a_time(page, base_url, login):
    login(seed.READER)
    page.goto(base_url + "testing")
    sum_tab = tab(page, seed.TASK_NAME)
    pair_tab = tab(page, seed.PAIR_TASK_NAME)
    sum_pane = page.locator("#test_" + seed.TASK_NAME)
    pair_pane = page.locator("#test_" + seed.PAIR_TASK_NAME)
    # Each pane has its own submission form, telling the tasks apart.
    sum_input = page.locator("input[type=file][name='sum.%l']")
    pair_input = page.locator("input[type=file][name='pair_a.%l']")

    expect(sum_tab).to_be_visible()
    expect(pair_tab).to_be_visible()
    expect(sum_pane).to_be_visible()
    expect(sum_input).to_be_visible()
    expect(pair_pane).to_be_hidden()
    expect(pair_input).to_be_hidden()

    pair_tab.click()
    expect(pair_pane).to_be_visible()
    expect(pair_input).to_be_visible()
    expect(sum_pane).to_be_hidden()
    expect(sum_input).to_be_hidden()

    sum_tab.click()
    expect(sum_pane).to_be_visible()
    expect(sum_input).to_be_visible()
    expect(pair_pane).to_be_hidden()
    expect(pair_input).to_be_hidden()


def test_testing_tab_shows_that_task_tests(page, base_url, login):
    login(seed.READER)
    page.goto(base_url + "testing")
    # Only the visible pane's table is exposed by role.
    tab(page, seed.PAIR_TASK_NAME).click()
    pane = page.locator("#test_" + seed.PAIR_TASK_NAME)
    expect(pane.locator("tr[data-user-test]")).to_be_visible()
    expect(page.locator(
        "#test_%s tr[data-user-test]" % seed.TASK_NAME)).to_be_hidden()


# Alerts.


def test_login_error_alert_can_be_dismissed(page, base_url, seeded):
    page.goto(base_url)
    page.get_by_label("Username").fill(seed.READER)
    page.get_by_label("Password").fill("not-the-password")
    page.get_by_role("button", name="Login").click()

    alert = page.get_by_text("Failed to log in.")
    expect(alert).to_be_visible()
    # The wrong password did not log the user in.
    expect(page.get_by_role("button", name="Logout")).to_have_count(0)
    page.get_by_role("button", name="Close").click()
    expect(alert).to_have_count(0)
    # Dismissing the alert does not break the rest of the page.
    expect(page.get_by_role("button", name="Login")).to_be_visible()


def test_notification_alerts_are_dismissed_one_at_a_time(
        page, base_url, login):
    login(seed.READER)
    # An announcement, a message and an answer exist before the login.
    alerts = page.locator("#notifications").get_by_role(
        "button", name="Close")
    expect(alerts).to_have_count(3)

    for remaining in (2, 1, 0):
        alerts.last.click()
        expect(alerts).to_have_count(remaining)
    # The unread counter is not tied to the alerts.
    expect(page.locator("#unread_count")).to_contain_text("3")


@pytest.mark.parametrize("level", ["error", "success", "warning"])
def test_script_built_notification_can_be_dismissed(
        page, base_url, login, level):
    # Notifications of type "notification" are sent by the administrators
    # and show their own title and text; build one as the page would.
    login(seed.NOBODY)
    page.evaluate(
        "utils.display_notification('notification', 0, 'Heads up', "
        "'Something happened', %r, true)" % level)
    title = page.get_by_role("heading", name="Heads up")
    expect(title).to_be_visible()
    expect(page.get_by_text("Something happened")).to_be_visible()

    # Pick the button inside the alert that holds our title.
    page.locator("#notifications > *").filter(has=title).get_by_role(
        "button", name="Close").click()
    expect(title).to_have_count(0)
    expect(page.get_by_text("Something happened")).to_have_count(0)
