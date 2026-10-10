"""Counter settings default on without overwriting existing preferences."""

from cmscontrib.updaters.update_51 import Updater


def test_counter_defaults_and_existing_preferences():
    data = {"_version": 50, "1": {"_class": "Contest"},
            "2": {"_class": "Contest", "show_task_scores_in_overview": False,
                  "show_task_scores_in_sidebar": False}}
    result = Updater(data).run()
    assert result["1"]["show_task_scores_in_overview"] is True
    assert result["1"]["show_task_scores_in_sidebar"] is True
    assert result["2"]["show_task_scores_in_overview"] is False
    assert result["2"]["show_task_scores_in_sidebar"] is False
