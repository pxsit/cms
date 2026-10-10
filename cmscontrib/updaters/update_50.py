"""Add notice mode and explicit task audiences to older dumps."""


class Updater:
    def __init__(self, data):
        assert data["_version"] == 49
        self.objs = data

    def run(self):
        for value in self.objs.values():
            if isinstance(value, dict) and value.get("_class") == "Task":
                value["is_notice"] = False
                value["restricted"] = False
                value["allowed_users"] = []
        self.objs["_version"] = 50
        return self.objs
