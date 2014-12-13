from datetime import time, timedelta, datetime


class Report(object):

    def __init__(self, connection, user, start_date, end_date):
        self.conn = connection
        self.user = user
        self.start_date = start_date
        self.end_date = end_date
        self.work_items = []
        self.issues = []
        self.day_reports = []
        self.current_date = self.start_date

    def process(self):
        issues = self.get_issues()
        for issue in issues:
            self.work_items += self.get_work_items(issue)

    def get_issues(self):
        start = self.start_date.strftime('%Y-%m-%d')
        end = datetime.today().strftime('%Y-%m-%d')
        filter = 'updated: {start} .. {end} updater: {user}'.format(start=start,
                                                                    end=end,
                                                                    user=self.user)
        return self.conn.get_issues(filter)

    def get_work_items(self, issue):
        end_timestamp = int((self.end_date + timedelta(days=1)).timestamp()) * 1000
        start_timestamp = int(self.start_date.timestamp()) * 1000
        work_items = self.conn.getWorkItems(issue.id)
        return [w for w in work_items
                if w.authorLogin == self.user and
                end_timestamp > int(w.date) >= start_timestamp]

    def report_day(self, day):
        return DayReport(day, self.work_items, self.issues)

    def run(self):
        self.issues = self.get_issues()
        for issue in self.issues:
            work_items = self.get_work_items(issue)
            self.work_items += work_items
        reports = []
        self.current_date = self.start_date
        while True:
            reports.append(self.report_day(self.current_date))
            if self.current_date == self.end_date:
                break
            self.current_date += timedelta(days=1)
        self.day_reports = reports

    def print(self):
        self.run()
        for report in self.day_reports:
            report.print()


class DayReport(object):

    def __init__(self, day, work_items, issues):
        self.day = day
        self.work_items = self.filter_work_items(work_items)
        issue_ids = self.get_issue_ids()
        self.issues = [i for i in issues if i.id in issue_ids]
        self.issue_reports = []

    def filter_work_items(self, work_items):
        start_timestamp = int(self.day.timestamp()) * 1000
        end_timestamp = int((self.day + timedelta(days=1)).timestamp()) * 1000
        return [w for w in work_items
                if end_timestamp > int(w.date) > start_timestamp]

    def get_issue_ids(self):
        return set([w.issue for w in self.work_items])

    def report_issue(self, issue):
        return IssueReport(issue, self.work_items)

    def run(self):
        reports = []
        for issue in self.issues:
            reports.append(IssueReport(issue, self.work_items))
        self.issue_reports = reports

    def print(self):
        self.run()
        print(self)
        for report in self.issue_reports:
            report.print()

    def __str__(self):
        return self.day.strftime("%Y-%m-%d")


class IssueReport(object):

    def __init__(self, issue, work_items):
        self.issue = issue
        self.work_items = [w for w in work_items if w.issue == issue.id]

    @property
    def total_time(self):
        duration = sum([int(w.duration) for w in self.work_items])
        hours = duration/60
        minutes = (hours % 1) * 60
        return time(int(hours), int(minutes))

    def print(self):
        print(self)

    def __str__(self):
        string = "{issue_id} :: {time} - {issue_title}"
        return string.format(issue_id=self.issue.id,
                             issue_title=self.issue.summary,
                             time=self.total_time)