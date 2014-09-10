from unittest import TestCase
from manictime import TogglRow
from youtrack.connection import Connection
import youtrack
import datetime
import csv
import codecs
__author__ = 'Matthew'


class TestTogglRow(TestCase):
    def setUp(self):
        connection = Connection("http://tracker.outlandishideas.co.uk", "matt", "strangeCharm")
        with codecs.open('TogglData.csv', 'rU', encoding='utf-8-sig') as fp:
            rows = csv.DictReader(fp)
            for row in rows:
                self.tr = TogglRow(connection, row)
                break

    def test_get_field(self):
        user = self.tr.get_field('User')
        email = self.tr.get_field('Email')
        client = self.tr.get_field('Client')
        project = self.tr.get_field('Project')
        task = self.tr.get_field('Task')
        description = self.tr.get_field('Description')
        billable = self.tr.get_field('Billable')
        start_date = self.tr.get_field('Start date')
        start_time = self.tr.get_field('Start time')
        end_date = self.tr.get_field('End date')
        end_time = self.tr.get_field('End time')
        duration = self.tr.get_field('Duration')
        tags = self.tr.get_field('Tags')
        amount = self.tr.get_field('Amount ()')
        self.assertEqual(user, "Mkendon")
        self.assertEqual(email, "mkendon@gmail.com")
        self.assertEqual(client, "me")
        self.assertEqual(project, "Test Project")
        self.assertEqual(task, "task")
        self.assertEqual(description, "Something")
        self.assertEqual(billable, "No")
        self.assertEqual(start_date, "2014-09-09")
        self.assertEqual(start_time, "10:00:00")
        self.assertEqual(end_date, "2014-09-09")
        self.assertEqual(end_time, "12:03:00")
        self.assertEqual(duration, "02:03:00")
        self.assertEqual(tags, "AFI-125")
        self.assertEqual(amount, "0")

    def test_get_issue_id(self):
        result = self.tr.get_issue_id()
        self.assertEqual(result, "AFI-125")

    def test_get_project_id(self):
        result = self.tr.get_project_id()
        self.assertEqual(result, "AFI")

    def test_get_duration(self):
        result = self.tr.get_duration()
        self.assertEqual(result, "02:03:00")

    def test_get_duration_split(self):
        result = self.tr.get_duration_split()
        self.assertEqual(result, "02:03:00".split(":"))

    def test_get_start(self):
        result = self.tr.get_start()
        self.assertEqual(result, "2014-09-09 10:00:00")

    def test_get_description(self):
        result = self.tr.get_description()
        self.assertEqual(result, "Something")

    def test_get_date_object(self):
        result = self.tr.get_date_object()
        self.assertIsInstance(result, datetime.date)

    def test_get_date_string(self):
        result = self.tr.get_date_string(None)
        self.assertEqual("2014-09-09", result)

    def test_get_date_as_unix_time(self):
        result = self.tr.get_date_as_unix_time()
        self.assertEqual(1410256800, result)

    def test_get_date_as_unix_time_milliseconds(self):
        result = self.tr.get_date_as_unix_time_milliseconds()
        self.assertEqual(1410256800000, result)

    def test_get_date_string_with_custom_format(self):
        result = self.tr.get_date_string("%d %m %Y")
        self.assertEqual("09 09 2014", result)

    def test_get_issue(self):
        result = self.tr.issue
        self.assertIsInstance(result, youtrack.Issue)

    def test_get_project(self):
        result = self.tr.project
        self.assertIsInstance(result, youtrack.Project)

    def test_get_timeslip_exists_no_timeslips(self):
        result = self.tr.timeslip_exists()
        self.assertIsInstance(result, bool)

    def test_get_timeslip_exists(self):
        self.tr.data['Name'] = "TP, TP-12"
        result = self.tr.timeslip_exists()
        self.assertIsInstance(result, bool)

    def test_create_timeslip(self):
        result = self.tr.create_timeslip()
        self.assertIsInstance(result, youtrack.WorkItem)
        self.assertEqual(result.date, self.tr.get_date_as_unix_time_milliseconds())
        self.assertEqual(result.duration, self.tr.get_duration_as_minutes())
        self.assertEqual(result.description, self.tr.get_description())