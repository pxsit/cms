"""Task audience enforcement, permanent modes, and notice endpoints."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cms.db import Task, User, Statement, Attachment
from cms.server.admin.handlers.task import (
    AddTaskHandler, TaskHandler, read_task_audience, read_notice_presentation)
from cms.server.contest.handlers.api import ApiSubmitHandler, ApiTaskListHandler
from cms.server.contest.handlers.task import (
    TaskDescriptionHandler, TaskStatementViewHandler, TaskAttachmentViewHandler)
from cms.server.contest.handlers.tasksubmission import TaskSubmissionsHandler
from cms.server.contest.handlers.taskusertest import UserTestHandler
from cms.server.contest.submission import (
    accept_submission, accept_user_test, UnacceptableSubmission, TestingNotAllowed)
import tornado.web


def user(name):
    return User(username=name, first_name=name, last_name="", password="")


@pytest.fixture
def task():
    return Task(name="notice", title="Any title", restricted=True, is_notice=True,
                allowed_users=[user("alice"), user("bob")])


def handler(cls, task, viewer):
    result = cls.__new__(cls)
    result.application = MagicMock()
    result.sql_session = MagicMock()
    result.sql_session.query.return_value.filter.return_value.filter.return_value.one_or_none.return_value = task
    result._current_user = SimpleNamespace(user=viewer, unrestricted=False)
    result.contest = task.contest
    result.impersonated_by_admin = False
    result.is_multi_contest = lambda: False
    result.r_params = {"actual_phase": 0}
    result.render = MagicMock()
    result.fetch = MagicMock()
    result.json = MagicMock()
    result.request = MagicMock()
    return result


def test_audience_is_explicit_and_independent_of_mode(task):
    assert task.is_visible_to(SimpleNamespace(user=task.allowed_users[0]))
    assert task.is_visible_to(SimpleNamespace(user=task.allowed_users[1]))
    assert not task.is_visible_to(SimpleNamespace(user=user("charlie")))
    task.allowed_users = []
    assert not task.is_visible_to(SimpleNamespace(user=user("alice")))
    task.restricted = False
    assert task.is_visible_to(SimpleNamespace(user=user("charlie")))
    assert not task.is_visible_to(None)


@pytest.mark.parametrize("notice,restricted,ranked", [
    (False, False, True), (False, True, False),
    (True, False, False), (True, True, False)])
def test_ranking_policy(task, notice, restricted, ranked):
    task.is_notice, task.restricted = notice, restricted
    assert task.ranked == ranked


@pytest.mark.parametrize("cls,args", [
    (TaskDescriptionHandler, ("notice",)),
    (TaskStatementViewHandler, ("notice", "en")),
    (TaskAttachmentViewHandler, ("notice", "file.txt")),
    (TaskSubmissionsHandler, ("notice",)),
])
def test_hidden_task_direct_urls_return_404(task, cls, args):
    request = handler(cls, task, user("outsider"))
    with pytest.raises(tornado.web.HTTPError) as error:
        request.get(*args)
    assert error.value.status_code == 404
    request.render.assert_not_called()
    request.fetch.assert_not_called()


def test_allowed_notice_description(task):
    request = handler(TaskDescriptionHandler, task, task.allowed_users[0])
    request.get(task.name)
    request.render.assert_called_once_with("task_description.html", task=task,
                                           **request.r_params)


@pytest.mark.parametrize("cls,args", [
    (TaskSubmissionsHandler, ("notice",)), (UserTestHandler, ("notice",))])
def test_allowed_notice_rejects_submission_and_testing_routes(task, cls, args):
    request = handler(cls, task, task.allowed_users[0])
    request.r_params["testing_enabled"] = True
    with pytest.raises(tornado.web.HTTPError) as error:
        getattr(request, "post" if cls is UserTestHandler else "get")(*args)
    assert error.value.status_code == 404


def test_api_submit_does_not_accept_notice(task):
    request = handler(ApiSubmitHandler, task, task.allowed_users[0])
    request.post(task.name)
    request.json.assert_called_once_with({"error": "Task not found"}, 404)
    request.sql_session.commit.assert_not_called()


def test_api_list_marks_notice_without_submission_format(task):
    request = handler(ApiTaskListHandler, task, task.allowed_users[0])
    request.r_params["visible_tasks"] = [task]
    request.get()
    request.json.assert_called_once_with({"tasks": [{
        "name": task.name, "statements": [], "submission_format": [],
        "is_notice": True}]})


@pytest.mark.parametrize("notice,allowed", [(True, True), (False, False)])
def test_submission_workflow_blocks_before_processing_files(task, notice, allowed):
    task.is_notice = notice
    viewer = task.allowed_users[0] if allowed else user("outsider")
    participation = SimpleNamespace(user=viewer, contest=task.contest)
    session, files = MagicMock(), MagicMock()
    with pytest.raises(UnacceptableSubmission):
        accept_submission(session, files, participation, task, datetime.now(),
                          {}, None, True, override_max_number=True,
                          override_min_interval=True)
    with pytest.raises(TestingNotAllowed):
        accept_user_test(session, files, participation, task, datetime.now(), {}, None)
    session.add.assert_not_called()
    files.put_file_content.assert_not_called()


@pytest.mark.parametrize("original,requested", [(True, "normal"), (False, "notice")])
def test_admin_cannot_convert_either_mode(task, original, requested):
    task.is_notice = original
    request = handler(TaskHandler, task, task.allowed_users[0])
    request._current_user = SimpleNamespace(permission_all=True)
    request.safe_get_item = MagicMock(return_value=task)
    request.get_argument = lambda name, default=None: requested if name == "task_mode" else default
    request.redirect = MagicMock()
    request.url = MagicMock()
    request.try_commit = MagicMock()
    request.post("1")
    assert task.is_notice == original
    request.try_commit.assert_not_called()
    notification = request.application.service.add_notification.call_args.args
    assert "cannot be changed" in notification[2]


@pytest.mark.parametrize("mode", ["normal", "notice"])
def test_creation_sets_permanent_mode_and_empty_private_audience(mode):
    request = handler(AddTaskHandler, Task(name="dummy", title="Dummy"), user("admin"))
    request._current_user = SimpleNamespace(permission_all=True)
    request.get_argument = lambda name, default=None: {
        "name": "custom_name", "task_mode": mode, "visibility": "selected"
    }.get(name, default)
    request.get_arguments = lambda name: []
    request.sql_session.query.return_value.filter.return_value.all.return_value = []
    request.try_commit = lambda: True
    request.redirect = MagicMock()
    request.url = MagicMock()
    request.post()
    created = request.sql_session.add.call_args_list[0].args[0]
    assert isinstance(created, Task)
    assert created.name == "custom_name"
    assert created.is_notice == (mode == "notice")
    assert created.restricted and created.allowed_users == []


def test_unknown_audience_user_is_rejected():
    request = MagicMock()
    request.get_argument.return_value = "selected"
    request.get_arguments.return_value = ["42"]
    request.sql_session.query.return_value.filter.return_value.all.return_value = []
    with pytest.raises(ValueError, match="Unknown user"):
        read_task_audience(request, {})


def test_missing_audience_fields_preserve_restrictions():
    request = MagicMock()
    request.get_argument.return_value = None
    attrs = {"restricted": True}
    read_task_audience(request, attrs)
    assert attrs == {"restricted": True}
    request.sql_session.query.assert_not_called()


@pytest.mark.parametrize("cls,args", [
    (TaskStatementViewHandler, ("notice", "en")),
    (TaskAttachmentViewHandler, ("notice", "file.txt"))])
def test_selected_users_can_download_notice_files(task, cls, args):
    task.statements["en"] = Statement(language="en", digest="a" * 64)
    task.attachments["file.txt"] = Attachment(filename="file.txt", digest="b" * 64)
    request = handler(cls, task, task.allowed_users[0])
    request.get(*args)
    request.fetch.assert_called_once()


def test_notice_template_renders_statement_without_grading_details(task):
    from jinja2 import ChoiceLoader, DictLoader
    from cms.server.contest.jinja2_toolbox import CWS_ENVIRONMENT

    task.statements["en"] = Statement(language="en", digest="a" * 64)
    env = CWS_ENVIRONMENT.overlay(loader=ChoiceLoader([
        DictLoader({"contest.html": "{% block core %}{% endblock %}"}),
        CWS_ENVIRONMENT.loader]))
    html = env.get_template("task_description.html").render(
        task=task, gettext=lambda message: message,
        contest_url=lambda *parts: "/" + "/".join(parts))
    assert task.title in html and 'class="label"' not in html
    assert "Download PDF" in html
    assert "Some details" not in html and "Time limit" not in html
    assert "Submissions" not in html


def test_edited_templates_compile():
    from cms.server.admin.jinja2_toolbox import AWS_ENVIRONMENT
    from cms.server.contest.jinja2_toolbox import CWS_ENVIRONMENT

    for name in ("add_task.html", "task.html", "task_audience.html", "notice_presentation.html"):
        AWS_ENVIRONMENT.get_template(name)
    for name in ("contest.html", "overview.html", "communication.html",
                 "task_description.html", "test_interface.html"):
        CWS_ENVIRONMENT.get_template(name)


def test_custom_html_is_sandboxed_and_pdf_button_is_independent(task):
    from bs4 import BeautifulSoup
    from jinja2 import ChoiceLoader, DictLoader
    from cms.server.contest.jinja2_toolbox import CWS_ENVIRONMENT

    task.notice_label = "For you"
    task.notice_intro_html = '<style>body { color: pink; }</style><h2>Hello</h2><script>parent.alert(1)</script>" onload="alert(1)'
    task.notice_button_text = '<img src=x onerror="alert(1)"> Read the letter'
    task.notice_button_color = "#123456"
    task.notice_button_radius = 24
    task.statements["en"] = Statement(language="en", digest="a" * 64)
    env = CWS_ENVIRONMENT.overlay(loader=ChoiceLoader([
        DictLoader({"contest.html": "{% block core %}{% endblock %}"}),
        CWS_ENVIRONMENT.loader]))
    html = env.get_template("task_description.html").render(
        task=task, gettext=lambda message: message,
        contest_url=lambda *parts: "/" + "/".join(parts))
    soup = BeautifulSoup(html, "html.parser")
    frame = soup.select_one("iframe.notice-introduction")
    assert frame["sandbox"] == []
    assert frame["srcdoc"] == task.notice_intro_html
    assert not frame.has_attr("onload")
    assert not soup.find("script") and not soup.find("img")
    button = soup.select_one("a.notice-pdf-button")
    assert button.get_text(strip=True) == task.notice_button_text
    assert button.has_attr("download")
    assert button["href"].startswith("/tasks/notice/statements/en/")
    assert "#123456" in button["style"] and "24px" in button["style"]
    assert frame.parent == button.parent.parent
    assert "For you" in html and "description</small>" not in html


@pytest.mark.parametrize("field,value", [
    ("notice_button_color", "red;position:fixed"),
    ("notice_button_text_color", "#fff"),
    ("notice_button_text", " "), ("notice_label", "x" * 121),
    ("notice_intro_height", "0"), ("notice_intro_height", "2001"),
    ("notice_button_radius", "-1"), ("notice_button_radius", "101")])
def test_invalid_notice_presentation_is_rejected(task, field, value):
    request = handler(TaskHandler, task, task.allowed_users[0])
    request.get_argument = lambda name, default=None: value if name == field else default
    with pytest.raises(ValueError):
        read_notice_presentation(request, task.get_attrs())


def test_notice_presentation_accepts_html_css_and_custom_labels(task):
    values = {"notice_label": "Open the letter", "notice_intro_html": "<h2>Hello</h2>",
              "notice_intro_height": "320", "notice_button_text": "Read it",
              "notice_button_color": "#abcdef", "notice_button_text_color": "#012345",
              "notice_button_radius": "12"}
    request = handler(TaskHandler, task, task.allowed_users[0])
    request.get_argument = lambda name, default=None: values.get(name, default)
    attrs = task.get_attrs()
    read_notice_presentation(request, attrs)
    assert attrs["notice_intro_html"] == values["notice_intro_html"]
    assert attrs["notice_button_text"] == "Read it"
    assert attrs["notice_intro_height"] == 320 and attrs["notice_button_radius"] == 12
