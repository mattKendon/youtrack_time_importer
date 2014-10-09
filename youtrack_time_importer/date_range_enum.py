__author__ = 'Matthew'

from collections import namedtuple
from enum import Enum
import datetime


today = datetime.date.today()
if today.weekday() == 0:
    # if monday get friday
    days = 3
    monday = today
else:
    days = 1
    monday = today - datetime.timedelta(days=today.weekday())

yesterday = (today - datetime.timedelta(days=days)).strftime('%Y-%m-%d')

DateRange = namedtuple('DateRange', ['since', 'until'])


class DateRangeEnum(Enum):
    last_week = DateRange(monday - datetime.timedelta(days=7), monday - datetime.timedelta(days=3))
    this_week = DateRange(monday, today)
    yesterday = DateRange(yesterday, yesterday)
    today = DateRange(today, today)

    def since(self):
        return self.value.since

    def until(self):
        return self.value.until


if __name__ == "__main__":
    last_week = DateRangeEnum.last_week
    today = DateRangeEnum.today
    this_week = DateRangeEnum.this_week
    yesterday = DateRangeEnum.yesterday
    print(last_week.since())
    print(last_week.until())
    print(today.since())
    print(today.until())
    print(this_week.since())
    print(this_week.until())
    print(yesterday.since())
    print(yesterday.until())
    print([name for name, member in DateRangeEnum.__members__.items()])
    a_name = "yesterday"
    yesterday = [member for name, member in DateRangeEnum.__members__.items() if name == a_name]
    print(yesterday[0].since())
    print(yesterday[0].until())
