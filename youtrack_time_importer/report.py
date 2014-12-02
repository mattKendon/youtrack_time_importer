from youtrack.connection import Connection
from collections import OrderedDict


class Report(object):

    def __init__(self, connection, user, start_date, end_date):
        self.conn = connection
        self.user = user
        self.start_date = start_date
        self.end_date = end_date
        self.work_items = []

    def report(self):
        issues = self.get_issues()
        for issue in issues:
            self.work_items += self.get_work_items(issue)
        for work_item in self.work_items:
            self.process_work_item(work_item)

    def get_issues(self):
        return self.conn.getIssues()

    def get_work_items(self, issue):
        return [w for w in issue.getWorkItems()
                if w.user == self.user and
                self.end_date > w.date > self.start_date]

    def process_work_item(self, work_item):
        pass