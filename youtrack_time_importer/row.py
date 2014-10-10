from youtrack import WorkItem
from youtrack import YouTrackException
import abc
import datetime
import re


class MetaRow(abc.ABCMeta):
    _ids = set()
    @property
    def ids(cls):
        return cls._ids
    @ids.setter
    def ids(cls, value):
        cls._ids.add(value)


class Row(metaclass=MetaRow):
    """abstract class to handle a row of data from a CSV or API call"""

    issue_finder = re.compile('(?P<issue_id>[a-zA-Z0-9]*\-[0-9]+)', flags=re.IGNORECASE)

    @abc.abstractproperty
    def datetime_format(self):
        pass

    @abc.abstractmethod
    def create_work_item(self):
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
        """

    @abc.abstractmethod
    def __str__(self):
        pass

    def __init__(self, data, connection):
        self.data = data
        self.connection = connection
        self._issue_id = None
        self._work_item = None

    @property
    def issue_id(self):
        if not self._issue_id:
            self._issue_id = self.find_issue_id()
        return self._issue_id

    @issue_id.setter
    def issue_id(self, value):
        self._issue_id = value

    @property
    def work_item(self):
        if not self._work_item:
            self._work_item = self.create_work_item()
        return self._work_item

    @work_item.setter
    def work_item(self, value):
        self._work_item = value

    def work_item_exists(self):
        """Checks to see if WorkItem already exists

        Gets all the WorkItems for an issue and checks to see if
        once exists with the same date and duration. As date is a timestamp
        based on date and time, this should be completely unique.

        Returns:
            Boolean value, returning True if it exists, and false if :
            it doesn't

        Raises:
            A YoutrackIssueNotFoundException if issue doesnt exist on server
        """

        try:
            work_items = self.connection.getWorkItems(self.issue_id)
        except YouTrackException as e:
            return False
        except TypeError as e:
            # no issue id
            return False
        else:
            for work_item in work_items:
                if (work_item.authorLogin == self.connection.login and
                        work_item.date == self.work_item.date and
                        work_item.duration == self.work_item.duration):
                    return True
            return False

    def save_work_item(self):
        """Saves WorkItem to Youtrack

        Uses the Youtrack Connection to save the WorkItem
        to the issue, if it is determined that the issue ID
        is correct.

        Args:
            work_item: A WorkItem object with description, duration
            and date all set

        Raises:
            A YoutrackMissingConnectionException if the connection object
            doesnt' have the method createWorkItem()
            a YoutrackIssueNotFoundException if issue doesnt exist on server,
            a YoutrackWorkItemIncorrectException if the work_item does not have
            all attributes
        """

        try:
            self.connection.createWorkItem(self.issue_id, self.work_item)
        except AttributeError as ae:
            if "createWorkItem" in ae.args[0]:
                raise YoutrackMissingConnectionException()
            else:
                raise YoutrackWorkItemIncorrectException()
        except TypeError as te:
            raise YoutrackIssueNotFoundException
        except YouTrackException as e:
            raise YoutrackIssueNotFoundException


class ManictimeRow(Row):
    datetime_format = "%d/%m/%Y %H:%M:%S"

    def create_work_item(self):
        work_item = WorkItem()

        description = self.data.get('Notes')
        duration = self.duration_as_minutes()
        date = round(self.start_datetime().timestamp()*1000)

        work_item.description = description
        work_item.duration = str(duration)
        work_item.date = str(date)

        return work_item

    def duration_as_minutes(self):
        duration = self.data.get('Duration').split(":")
        return int(duration[0])*60 + int(duration[1]) + round(float(duration[2])/60)

    def start_datetime(self):
        """Return a datetime object representation of the start date and time"""

        return datetime.datetime.strptime(self.data.get('Start'), self.datetime_format)

    def __str__(self):
        tags = self.data.get("Name")
        description = self.data.get("Notes")
        time = self.start_datetime().strftime("%H:%M")
        date = self.start_datetime().strftime("%d/%m/%y")
        return "{tags} / {d} - {t} {dt}".format(tags=tags, d=description, t=time, dt=date)

    def is_ignored(self):
        return "ignore" in self.data.get("Name")

    def find_issue_id(self):
        match = self.issue_finder.search(self.data.get("Name"))
        try:
            return match.group('issue_id')
        except AttributeError as e:
            return False

    def save_work_item(self):
        # super().save_work_item()
        pass


class TogglCSVRow(Row):
    datetime_format = "%Y-%m-%d %H:%M:%S"

    def create_work_item(self):
        work_item = WorkItem()

        description = self.data.get('Description')
        duration = self.duration_as_minutes()
        date = round(self.start_datetime().timestamp()*1000)

        work_item.description = description
        work_item.duration = str(duration)
        work_item.date = str(date)

        return work_item

    def duration_as_minutes(self):
        duration = self.data.get('Duration').split(":")
        return int(duration[0])*60 + int(duration[1]) + round(float(duration[2])/60)

    def start_datetime(self):
        """Return a datetime object representation of the start date and time"""

        start = "{0} {1}".format(self.data.get('Start date'), self.data.get('Start time'))
        return datetime.datetime.strptime(start, self.datetime_format)

    def __str__(self):
        description = self.data.get("Description")
        time = self.start_datetime().strftime("%H:%M")
        date = self.start_datetime().strftime("%d/%m/%y")
        return "{d} - {t} {dt}".format(d=description, t=time, dt=date)

    def is_ignored(self):
        return "ignore" in self.data.get("Tags")

    def find_issue_id(self):
        match = self.issue_finder.search(self.data.get("Description"))
        try:
            return match.group('issue_id')
        except AttributeError as e:
            return False


class TogglAPIRow(Row):
    datetime_format = "%Y-%m-%dT%H:%M:%S"

    def create_work_item(self):
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
        match = self.issue_finder.search(self.data.get("description"))
        try:
            return match.group('issue_id')
        except AttributeError as e:
            return False

    def start_datetime(self):
        """Return a datetime object representation of the start date and time"""

        start = self.data.get('start').split("+")[0]
        return datetime.datetime.strptime(start, self.datetime_format)

    def save_work_item(self):
        super().save_work_item()
        cls = type(self)
        cls.ids = self.data.get('id')


class YoutrackIssueNotFoundException(Exception):
    pass


class YoutrackWorkItemIncorrectException(Exception):
    pass


class YoutrackMissingConnectionException(Exception):
    pass

