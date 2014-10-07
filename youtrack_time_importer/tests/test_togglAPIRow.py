from unittest import TestCase
from youtrack_time_importer.row import TogglAPIRow
from youtrack import WorkItem
__author__ = 'Matthew'


class TestTogglAPIRow(TestCase):
    def setUp(self):
        self.data = {
            'user': 'Mkendon',
            'tags': ['Youtracked'],
            'use_stop': True,
            'description': 'BCSM-15 Support new presences in code',
            'dur': 12294000,
            'billable': None,
            'pid': 6337533,
            'tid': None,
            'cur': None,
            'is_billable': False,
            'end': '2014-10-06T18:29:54+01:00',
            'updated': '2014-10-06T22:43:19+01:00',
            'start': '2014-10-06T15:05:00+01:00',
            'client': 'British Council',
            'task': None, 'project':
            'Social Monitor',
            'id': 166078570,
            'uid': 907967
        }
        self.row = TogglAPIRow(self.data)

    def test_work_item(self):
        work_item = self.row.work_item()
        self.assertIsInstance(work_item, WorkItem)
        self.assertEqual('BCSM-15 Support new presences in code', work_item.description)
        self.assertEqual('205', work_item.duration)
        self.assertEqual('1412604300000', work_item.date)

    def test__str__(self):
        self.assertEqual(self.row.__str__(), "BCSM-15 Support new presences in code - 15:05 06/10/14")

    def test_is_ignored(self):
        self.assertFalse(self.row.is_ignored())

    def test_is_ignored_when_ignore_tag_is_present(self):
        self.row.data.get("tags").append("ignore")
        self.assertTrue(self.row.is_ignored())

    def test_find_issue_id(self):
        self.assertEqual('BCSM-15', self.row.find_issue_id())

    def test_find_issue_id_return_false_if_no_issue_id(self):
        self.row.data['description'] = "Support new presences in code"
        self.assertFalse(self.row.find_issue_id())

    def test_find_project_id(self):
        self.assertEqual("BCSM", self.row.find_project_id())

    def test_find_project_id_returns_false_if_no_issue_id(self):
        self.row.data['description'] = "Support new presences in code"
        self.assertFalse(self.row.find_project_id())
