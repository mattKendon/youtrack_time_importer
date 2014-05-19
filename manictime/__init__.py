__author__ = 'Matthew'

from youtrack.connection import Connection
import codecs
import csv
import datetime
import re
import youtrack


class ManicTimeRow(object):
    def __init__(self, connection, data):
        self.connection = connection
        self.data = data
        self._issue = None
        self._project = None

    @property
    def issue(self):
        if not self.get_issue_id():
            self._issue = False
        if self._issue is None:
            try:
                result = self.connection.get_issue(self.get_issue_id())
                if result:
                    self._issue = result
                else:
                    self._issue = False
            except youtrack.YouTrackException as e:
                self._issue = False
        return self._issue

    @property
    def project(self):
        if self._project is None:
            result = self.connection.getProject(self.get_project_id())
            if result:
                self._project = result
            else:
                self._project = False
        return self._project

    def issue_exists(self):
        issue = self.issue
        if issue:
            return True
        else:
            return False

    def get_field(self, field_key):
        if field_key in self.data:
            return self.data[field_key]
        return None

    def get_tags(self):
        return self.get_field('Name')

    def get_issue_id(self):
        tags = self.get_tags()
        if not tags:
            return None
        pattern = '(?P<issue_id>[a-zA-Z0-9]*\-[0-9]+)'
        match = re.search(pattern, tags)
        if match:
            issue_id = match.group('issue_id')
            return issue_id
        else:
            return None

    def get_project_id(self):
        issue_id = self.get_issue_id()
        if issue_id:
            splits = issue_id.split('-')
            return splits[0]
        else:
            return None

    def get_duration(self):
        return self.get_field('Duration')

    def get_duration_split(self):
        duration = self.get_duration()
        if duration:
            return duration.split(':')
        else:
            return None

    def get_duration_as_string(self):
        duration = self.get_duration_split()
        time_string = None
        if duration:
            time_string = ""
            if int(duration[2]) >= 30:
                duration[1] = str(int(duration[1])+1)
            if int(duration[1]) > 0:
                if int(duration[1]) > 59:
                    duration[0] = str(int(duration[0])+1)
                    duration[1] = "0"
                else:
                    time_string = duration[1] + "m"
            if int(duration[0]) > 0:
                time_string = duration[0] + "h" + time_string
        return time_string

    def get_duration_as_minutes(self):
        duration = self.get_duration_split()
        minutes = None
        if duration:
            minutes = 0
            minutes += int(duration[0]) * 60
            minutes += int(duration[1])
            if int(duration[2]) >= 30:
                minutes += 1
        return minutes

    def get_start(self):
        return self.get_field('Start')

    def get_date_object(self):
        date_string = self.get_start()
        date = None
        if date_string:
            date = datetime.datetime.strptime(date_string, "%d/%m/%Y %H:%M:%S")
        return date

    def get_date_string(self, date_format):
        if not date_format:
            date_format = "%Y-%m-%d"
        date = self.get_date_object()
        date_string = None
        if date:
            date_string = date.strftime(date_format)
        return date_string

    def get_description(self):
        return self.get_field("Notes")

    def get_date_as_unix_time(self):
        dt = self.get_date_object()
        if dt:
            epoch = datetime.datetime.utcfromtimestamp(0)
            delta = dt - epoch
            return int(delta.total_seconds())
        else:
            return None

    def get_date_as_unix_time_milliseconds(self):
        epoch = self.get_date_as_unix_time()
        if epoch:
            return epoch * 1000
        else:
            return None

    def create_timeslip(self):
        timeslip = youtrack.WorkItem()
        timeslip.description = self.get_description()
        timeslip.date = self.get_date_as_unix_time_milliseconds()
        timeslip.duration = self.get_duration_as_minutes()
        return timeslip

    def get_timeslips(self):
        timeslips = self.connection.getWorkItems(self.get_issue_id())
        return timeslips

    def timeslip_exists(self):
        timeslips = self.get_timeslips()
        if timeslips:
            for timeslip in timeslips:
                if timeslip.duration == str(self.get_duration_as_minutes()) and \
                        timeslip.date == str(self.get_date_as_unix_time_milliseconds()) and \
                        timeslip.description == self.get_description():
                            return True
        return False

    def save(self):
        timeslip = self.create_timeslip()
        issue_id = self.get_issue_id()
        if issue_id and timeslip:
            return self.connection.createWorkItem(issue_id, timeslip)
        else:
            return False

    def timeslip_string(self):
        string_list = [
            self.get_date_string("%a, %d %b"),
            self.get_duration_as_string(),
            self.get_description()]

        return " / ".join(string_list)

if __name__ == '__main__':

    url = input("Enter in the YouTrack Url (http://tracker.outlandishideas.co.uk): ")
    if not url:
        url = "http://tracker.outlandishideas.co.uk"
    username = input("Enter in your YouTrack username: ")
    password = input("Enter in your YouTrack password: ")

    try:
        connection = Connection(url, username, password)
        user = connection.getUser(username)
    except youtrack.YouTrackException as e:
        exit("Could not connect to YouTrack")

    fileLocation = "c:/Users/Matthew/Desktop/ManicTimeData.csv"

    with codecs.open(fileLocation, 'rU', encoding='utf-8-sig') as fp:
        rows = csv.DictReader(fp)
        print("Importing timeslips from " + fileLocation + " ...")
        count = 0
        total = 0
        for row in rows:
            total += 1
            row = ManicTimeRow(connection, row)
            ignore = False

            if re.search('ignore', row.get_tags(), re.IGNORECASE):
                ignore = True
            else:
                if not row.get_issue_id() \
                        or (row.get_issue_id() and not row.issue_exists()):
                    response = input("  No Issue found for \"" + row.get_tags() + "\". Add to an issue? (y/n): ")
                    if response.strip() == "n":
                        ignore = True
                    else:
                        response = input("  Enter Issue Id for " + row.timeslip_string()
                                         + " (Leave blank to ignore): ")
                        while True:
                            if response == "":
                                ignore = True
                                break
                            if row.get_issue_id() or (row.get_issue_id() and not row.issue_exists()):
                                break
                            response = input("  Could not find issue. Please try again: ")

            if not ignore:
                if not row.timeslip_exists():
                        count += 1
                        row.save()
                        print("    uploaded timeslip")
                else:
                    print("  Timeslip for " + row.get_issue_id() + " (" +
                                     row.timeslip_string() + ") already exists")
            else:
                print("  Timeslip ignored")

        print("Added " + str(count) + " timeslips out of " + str(total))
        print("")

