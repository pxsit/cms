"""Task audiences persist by account identity and survive dump conversion."""

import unittest

from cmscontrib.DumpExporter import DumpExporter
from cmscontrib.DumpImporter import DumpImporter
from cmstestsuite.unit_tests.databasemixin import DatabaseMixin


class TestTaskAudience(DatabaseMixin, unittest.TestCase):
    def test_membership_survives_rename_and_visibility_changes(self):
        participant = self.add_participation()
        task = self.add_task(contest=participant.contest, restricted=True,
                             is_notice=True, allowed_users=[participant.user])
        self.session.flush()
        self.session.expire_all()
        self.assertTrue(task.is_visible_to(participant))
        participant.user.username += "_renamed"
        self.session.flush()
        self.assertTrue(task.is_visible_to(participant))
        task.restricted = False
        self.session.flush()
        task.restricted = True
        self.session.flush()
        self.session.expire_all()
        self.assertEqual(task.allowed_users, [participant.user])
        task.allowed_users = []
        self.session.flush()
        self.session.expire_all()
        self.assertFalse(task.is_visible_to(participant))

    def test_deleting_account_cannot_grant_access_to_another(self):
        selected = self.add_user()
        task = self.add_task(restricted=True, allowed_users=[selected])
        self.session.flush()
        self.session.delete(selected)
        self.session.flush()
        self.session.expire_all()
        self.assertEqual(task.allowed_users, [])

    def test_dump_uses_account_references_and_skip_users_is_fail_closed(self):
        selected = self.add_user()
        task = self.add_task(restricted=True, is_notice=True, allowed_users=[selected])
        self.session.flush()
        exporter = DumpExporter.__new__(DumpExporter)
        exporter.skip_submissions = exporter.skip_user_tests = False
        exporter.skip_users = exporter.skip_generated = False
        exporter.ids, exporter.queue = {}, []
        data = exporter.export_object(task)
        self.assertEqual(data["allowed_users"], ["0"])
        importer = DumpImporter.__new__(DumpImporter)
        imported_user = importer.import_object(exporter.export_object(selected))
        importer.objs = {"0": imported_user}
        imported_task = importer.import_object(data)
        importer.add_relationships(data, imported_task)
        self.assertTrue(imported_task.is_notice and imported_task.restricted)
        self.assertEqual(imported_task.allowed_users, [imported_user])
        self.assertIsNot(imported_user, selected)
        exporter.skip_users = True
        private_without_users = exporter.export_object(task)
        self.assertNotIn("allowed_users", private_without_users)
        self.assertTrue(private_without_users["restricted"])
