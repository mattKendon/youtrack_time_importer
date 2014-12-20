import csv
import abc
import requests
from parsedatetime import Calendar
from datetime import date

from dateutil.parser import parse as date_parse

from youtrack_time_importer.row import TogglAPIRow, TogglCSVRow, ManictimeRow


class Source(metaclass=abc.ABCMeta):

    def __init__(self):
        self._rows = []

    @abc.abstractproperty
    def row(self):
        pass

    @property
    def rows(self):
        if len(self._rows) < 1:
            for raw_row in self.get_rows():
                self._rows.append(self.row(raw_row))

        return self._rows

    @abc.abstractmethod
    def get_rows(self):
        return []

    def __iter__(self):
        return self.rows.__iter__()

    def __next__(self):
        return self.rows.__iter__().__next__()

    def __len__(self):
        return len(self.rows)


class CSVSource(Source, metaclass=abc.ABCMeta):

    def __init__(self, file):
        self.file = file
        super().__init__()

    @abc.abstractproperty
    def row(self):
        pass

    def get_rows(self):
        rows = []
        reader = csv.DictReader(self.file)
        for row_data in reader:
            rows.append(row_data)
        return rows


class APISource(Source, metaclass=abc.ABCMeta):

    def __init__(self):
        self._start = None
        self._end = None
        self.start = 'yesterday'
        self.end = 'yesterday'
        super().__init__()

    @abc.abstractproperty
    def row(self):
        pass

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start_string):
        self._start = APISource.to_date(start_string)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end_string):
        self._end = APISource.to_date(end_string)

    @abc.abstractmethod
    def get_rows(self):
        pass

    @staticmethod
    def to_date(date_string):
        if isinstance(date_string, date):
            return date_string
        cal = Calendar()
        try:
            dt = date_parse(date_string)
        except TypeError:
            dt = cal.nlp(date_string)[0][0]
        return dt


class ToggleCSVSource(CSVSource):
    row = TogglCSVRow

    def __init__(self, file):
        super().__init__(file)


class ToggleAPISource(APISource):
    row = TogglAPIRow

    def __init__(self, token, workspace_id):
        self.url = "https://toggl.com/reports/api/v2/details"
        self.user_agent = "matt@outlandish.com"
        self.token = token
        self.secret = "api_token"
        self.workspace_id = workspace_id
        super().__init__()

    @property
    def params(self):
        return {
            'workspace_id': self.workspace_id,
            'since': self.start,
            'until': self.end,
            'user_agent': self.user_agent
        }

    @property
    def auth(self):
        a = (self.token, self.secret)
        return a

    def get_rows(self):
        result = requests.get(self.url, auth=self.auth, params=self.params)
        return result.json()['data']


class ManictimeSource(CSVSource):
    row = ManictimeRow

    def __init__(self, file):
        super().__init__(file)

