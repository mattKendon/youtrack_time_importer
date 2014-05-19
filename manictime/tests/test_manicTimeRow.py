from unittest import TestCase
from manictime import ManicTimeRow
from youtrack.connection import Connection
import youtrack
import datetime
import csv
import codecs
__author__ = 'Matthew'


class TestManicTimeRow(TestCase):
    def setUp(self):
        connection = Connection("http://tracker.outlandishideas.co.uk", "matt", "strangeCharm")
        with codecs.open('ManicTimeData.csv', 'rU', encoding='utf-8-sig') as fp:
            rows = csv.DictReader(fp)
            for row in rows:
                self.mtr = ManicTimeRow(connection, row)
                break

    def test_get_field(self):
        name = self.mtr.get_field('Name')
        start = self.mtr.get_field('Start')
        end = self.mtr.get_field('End')
        duration = self.mtr.get_field('Duration')
        notes = self.mtr.get_field('Notes')
        self.assertEqual(name, "33DLP, 33DLP-269")
        self.assertEqual(start, "15/05/2014 10:15:43")
        self.assertEqual(end, "15/05/2014 10:30:37")
        self.assertEqual(duration, "0:14:54")
        self.assertEqual(notes, "Test Note")

    def test_get_issue_id(self):
        result = self.mtr.get_issue_id()
        self.assertEqual(result, "33DLP-269")

    def test_get_project_id(self):
        result = self.mtr.get_project_id()
        self.assertEqual(result, "33DLP")

    def test_get_duration(self):
        result = self.mtr.get_duration()
        self.assertEqual(result, "0:14:54")

    def test_get_duration_split(self):
        result = self.mtr.get_duration_split()
        self.assertEqual(result, "0:14:54".split(":"))

    def test_get_duration_as_string_with_no_hour(self):
        self.mtr.data['Duration'] = "0:14:29"
        result = self.mtr.get_duration_as_string()
        self.assertEqual(result, "14m")

    def test_get_duration_as_string_with_hour(self):
        self.mtr.data['Duration'] = "1:14:29"
        result = self.mtr.get_duration_as_string()
        self.assertEqual(result, "1h14m")

    def test_get_duration_as_string_with_second_above_29(self):
        self.mtr.data['Duration'] = "0:14:30"
        result = self.mtr.get_duration_as_string()
        self.assertEqual(result, "15m")

    def test_get_duration_as_string_with_second_above_29_and_minutes_at_59(self):
        self.mtr.data['Duration'] = "0:59:30"
        result = self.mtr.get_duration_as_string()
        self.assertEqual(result, "1h")

    def test_get_duration_as_minutes_with_no_hour(self):
        self.mtr.data['Duration'] = "0:14:29"
        result = self.mtr.get_duration_as_minutes()
        self.assertEqual(result, 14)

    def test_get_duration_as_minutes_with_hour(self):
        self.mtr.data['Duration'] = "1:14:29"
        result = self.mtr.get_duration_as_minutes()
        self.assertEqual(result, 74)

    def test_get_duration_as_minutes_with_second_above_29(self):
        self.mtr.data['Duration'] = "0:14:30"
        result = self.mtr.get_duration_as_minutes()
        self.assertEqual(result, 15)

    def test_get_duration_as_minutes_with_second_above_29_and_minutes_at_59(self):
        self.mtr.data['Duration'] = "0:59:30"
        result = self.mtr.get_duration_as_minutes()
        self.assertEqual(result, 60)

    def test_get_start(self):
        result = self.mtr.get_start()
        self.assertEqual(result, "15/05/2014 10:15:43")

    def test_get_description(self):
        result = self.mtr.get_description()
        self.assertEqual(result, "Test Note")

    def test_get_date_object(self):
        result = self.mtr.get_date_object()
        self.assertIsInstance(result, datetime.date)

    def test_get_date_string(self):
        result = self.mtr.get_date_string(None)
        self.assertEqual("2014-05-15", result)

    def test_get_date_as_unix_time(self):
        result = self.mtr.get_date_as_unix_time()
        self.assertEqual(1400148943, result)

    def test_get_date_as_unix_time_milliseconds(self):
        result = self.mtr.get_date_as_unix_time_milliseconds()
        self.assertEqual(1400148943000, result)

    def test_get_date_string_with_custom_format(self):
        result = self.mtr.get_date_string("%d %m %Y")
        self.assertEqual("15 05 2014", result)

    def test_get_issue(self):
        result = self.mtr.issue
        self.assertIsInstance(result, youtrack.Issue)

    def test_get_project(self):
        result = self.mtr.project
        self.assertIsInstance(result, youtrack.Project)

    def test_get_timeslip_exists_no_timeslips(self):
        result = self.mtr.timeslip_exists()
        self.assertIsInstance(result, bool)

    def test_get_timeslip_exists(self):
        self.mtr.data['Name'] = "TP, TP-12"
        result = self.mtr.timeslip_exists()
        self.assertIsInstance(result, bool)

    def test_create_timeslip(self):
        result = self.mtr.create_timeslip()
        self.assertIsInstance(result, youtrack.WorkItem)
        self.assertEqual(result.date, self.mtr.get_date_as_unix_time_milliseconds())
        self.assertEqual(result.duration, self.mtr.get_duration_as_minutes())
        self.assertEqual(result.description, self.mtr.get_description())

    def test_save(self):
        self.mtr.data['Name'] = "TP, TP-12"
        result = self.mtr.save()
        print(result)