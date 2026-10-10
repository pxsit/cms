"""Restricted tasks disappear from ranking data, including existing scores."""

from datetime import datetime
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cms.db import Task
from cms.io.priorityqueue import QueueEntry
from cms.service.ProxyService import (
    CannotSendError, ProxyExecutor, ProxyOperation, ProxyService, safe_delete_task)
from cmsranking.Scoring import ScoringStore
from cmsranking.Store import Store
from cmsranking.Subchange import Subchange
from cmsranking.Submission import Submission
from cmsranking.Task import Task as RankingTask


def entry(type_, data, index=0):
    return QueueEntry(ProxyOperation(type_, data), 2, datetime.now(), index)


def test_executor_drops_pending_scores_for_deleted_task():
    executor = ProxyExecutor("https://ranking.example/")
    entries = [entry(ProxyExecutor.TASK_TYPE, {"private": None}),
               entry(ProxyExecutor.SUBMISSION_TYPE, {
                   "1": {"task": "private"}, "2": {"task": "public"}}),
               entry(ProxyExecutor.SUBCHANGE_TYPE, {
                   "1s": {"submission": "1"}, "2s": {"submission": "2"}})]
    sent = []
    with patch("cms.service.ProxyService.safe_delete_task") as delete, \
            patch("cms.service.ProxyService.safe_put_data",
                  side_effect=lambda rank, path, data, op: sent.append(deepcopy(data))):
        executor.execute(entries)
    delete.assert_called_once_with("https://ranking.example/", "private")
    assert sent == [{"2": {"task": "public"}}, {"2s": {"submission": "2"}}]


def test_later_public_update_supersedes_queued_deletion():
    executor = ProxyExecutor("https://ranking.example/")
    public = {"name": "Public"}
    entries = [entry(ProxyExecutor.TASK_TYPE, {"task": None}),
               entry(ProxyExecutor.TASK_TYPE, {"task": public})]
    sent = []
    with patch("cms.service.ProxyService.safe_delete_task") as delete, \
            patch("cms.service.ProxyService.safe_put_data",
                  side_effect=lambda rank, path, data, op: sent.append(deepcopy(data))):
        executor.execute(entries)
    delete.assert_not_called()
    assert sent == [{"task": public}]


def test_failed_deletion_is_retried():
    executor = ProxyExecutor("https://ranking.example/")
    pending = entry(ProxyExecutor.TASK_TYPE, {"task": None})
    executor.enqueue = MagicMock()
    with patch("cms.service.ProxyService.safe_delete_task", side_effect=CannotSendError), \
            patch("cms.service.ProxyService.gevent.sleep"):
        executor.execute([pending])
    executor.enqueue.assert_called_once_with(pending.item, pending.priority, pending.timestamp)


@pytest.mark.parametrize("status", [204, 404])
def test_deletion_is_idempotent(status):
    with patch("cms.service.ProxyService.requests.delete") as delete:
        delete.return_value.status_code = status
        safe_delete_task("https://user:pass@ranking.example/", "private")


def test_unranked_tasks_never_produce_score_or_token_operations():
    proxy = ProxyService.__new__(ProxyService)
    for notice, restricted in [(True, False), (False, True), (True, True)]:
        task = Task(name="task", title="Task", is_notice=notice, restricted=restricted)
        submission = SimpleNamespace(task=task)
        assert proxy.operations_for_score(submission) == []
        assert proxy.operations_for_token(submission) == []


def test_reinitialize_replays_scores_and_tokens_immediately():
    proxy = ProxyService.__new__(ProxyService)
    proxy.scores_sent_to_rankings = {1}
    proxy.tokens_sent_to_rankings = {1}
    proxy.initialize = MagicMock()
    proxy._missing_operations = MagicMock()
    proxy.reinitialize()
    assert not proxy.scores_sent_to_rankings
    assert not proxy.tokens_sent_to_rankings
    proxy.initialize.assert_called_once()
    proxy._missing_operations.assert_called_once()


def test_ranking_task_deletion_removes_scores_and_history(tmp_path):
    stores = {}
    stores["subchange"] = Store(Subchange, str(tmp_path / "changes"), stores)
    stores["submission"] = Store(Submission, str(tmp_path / "submissions"), stores,
                                  [stores["subchange"]])
    stores["task"] = Store(RankingTask, str(tmp_path / "tasks"), stores,
                            [stores["submission"]])
    for store in stores.values():
        store.load_from_disk()
    scoring = ScoringStore(stores)
    task_data = {"name": "Private", "short_name": "private", "contest": "contest",
                 "max_score": 100.0, "score_precision": 0, "extra_headers": [],
                 "order": 0, "score_mode": "max"}
    stores["task"].create("private", task_data)
    stores["submission"].create("1", {"user": "alice", "task": "private", "time": 1})
    stores["subchange"].create("1s", {"submission": "1", "time": 2, "score": 100.0})
    assert scoring.get_score("alice", "private") == 100.0
    stores["task"].delete("private")
    assert scoring.get_score("alice", "private") == 0
    assert list(scoring.get_global_history()) == []
    assert not stores["submission"]._store and not stores["subchange"]._store
    assert not (tmp_path / "tasks" / "private.json").exists()
