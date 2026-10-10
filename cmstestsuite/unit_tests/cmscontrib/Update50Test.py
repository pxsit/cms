"""Older dumps keep their existing task behavior."""

from cmscontrib.updaters.update_50 import Updater


def test_existing_tasks_remain_public_normal_tasks():
    data = {"_version": 49, "1": {"_class": "Task", "name": "task"},
            "2": {"_class": "User", "username": "alice"}}
    updated = Updater(data).run()
    assert updated["1"] == {"_class": "Task", "name": "task", "is_notice": False,
                             "restricted": False, "allowed_users": []}
    assert updated["2"] == {"_class": "User", "username": "alice"}
