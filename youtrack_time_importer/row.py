from youtrack import WorkItem
import abc
import datetime
import re


class Row(metaclass=abc.ABCMeta):
    """abstract class to handle a row of data from a CSV or API call"""

    issue = None

    project = None

    connection = None

    issue_finder = re.compile('(?P<issue_id>[a-zA-Z0-9]*\-[0-9]+)', flags=re.IGNORECASE)

    data = dict()

    @abc.abstractproperty
    def datetime_format(self):
        pass

    @abc.abstractmethod
    def work_item(self):
        """Return WorkItem object with correctly formatted properties

        Creates a WorkItem object and then adds the three required properties
        for passing the object successfully to the Youtrack API to be added
        to a Youtrack Issue

        Returns:
            The WorkItem object with the three properties: description, duration,
            date.

            Description is a short description of the time entry.
            Duration is the duration of the time entry in minutes
            Date is a Unix Timestamp * 1000 (milliseconds not seconds)
        """

    @abc.abstractmethod
    def is_ignored(self):
        """Test whether this row should be ignored

        Ignored rows should not be uploaded to Youtrack. This method
        checks the conditions for ignoring a row against the row's data
        and returns the result as a boolean value.

        Returns:
            A boolean, which is True if this row is to be ignored
            and False if the row is not to be ignored.
        """

    @abc.abstractmethod
    def find_issue_id(self):
        """Return the issue ID from the row's data

        This will find the issue ID in the rows data using regular
        expressions to do so.

        Returns:
            A string in the form ABC-123, where ABC is the project ID
            in youtrack and 123 is the issue's number in that project.

        Raises:
            RowHasNoIssueIdException
        """

    @abc.abstractmethod
    def __str__(self):
        pass

    def __init__(self, data):
        self.data = data


class TogglCSVRow(Row):
    datetime_format = "%Y-%m-%d %H:%M:%S"

    def description(self):
        return self.data.get("description")


class TogglAPIRow(Row):
    datetime_format = "%Y-%m-%dT%H:%M:%S"

    def work_item(self):
        work_item = WorkItem()

        description = self.data.get("description")
        duration = round(self.data.get("dur")/1000/60)
        date = round(self.start_datetime().timestamp()*1000)

        work_item.description = description
        work_item.duration = str(duration)
        work_item.date = str(date)
        return work_item

    def __str__(self):
        description = self.data.get("description")
        time = self.start_datetime().strftime("%H:%M")
        date = self.start_datetime().strftime("%d/%m/%y")
        return "{d} - {t} {dt}".format(d=description, t=time, dt=date)

    def is_ignored(self):
        return "ignore" in self.data.get("tags")

    def find_issue_id(self):
        match = self.issue_finder.search(self.data.get("description"))#
        if match is None:
            # raise error
            pass
        else:
            return match.group('issue_id')

    def start_datetime(self):
        """Return a datetime object representation of the start date and time"""

        start = self.data.get('start').split("+")[0]
        return datetime.datetime.strptime(start, self.datetime_format)



