"""Older dumps gain presentation defaults without losing custom content."""

from cmscontrib.updaters.update_52 import Updater


def test_notice_presentation_defaults():
    data = {"_version": 51, "1": {"_class": "Task"},
            "2": {"_class": "Task", "notice_button_text": "Read me"}}
    updated = Updater(data).run()
    assert updated["1"]["notice_intro_html"] == ""
    assert updated["1"]["notice_label"] == "Statement"
    assert updated["1"]["notice_button_text"] == "Download PDF"
    assert updated["2"]["notice_button_text"] == "Read me"
