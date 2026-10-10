"""Add the task counter settings to older contest dumps."""


class Updater:
    def __init__(self, data):
        assert data["_version"] == 50
        self.objs = data

    def run(self):
        for value in self.objs.values():
            if isinstance(value, dict) and value.get("_class") == "Contest":
                value.setdefault("show_task_scores_in_overview", True)
                value.setdefault("show_task_scores_in_sidebar", True)
        return self.objs
