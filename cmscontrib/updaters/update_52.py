"""Add per-notice HTML and PDF button presentation settings."""


class Updater:
    def __init__(self, data):
        assert data["_version"] == 51
        self.objs = data

    def run(self):
        defaults = {
            "notice_label": "Statement", "notice_intro_html": "",
            "notice_intro_height": 240, "notice_button_text": "Download PDF",
            "notice_button_color": "#8b5963", "notice_button_text_color": "#ffffff",
            "notice_button_radius": 6,
        }
        for value in self.objs.values():
            if isinstance(value, dict) and value.get("_class") == "Task":
                for key, default in defaults.items():
                    value.setdefault(key, default)
        return self.objs
