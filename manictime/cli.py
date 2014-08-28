__author__ = 'Matthew'
import click
from dateutil.parser import parse as date_parse
import datetime
from youtrack.connection import Connection
import codecs
import csv
import re
import youtrack as yt
from manictime import ManicTimeRow


@click.group()
def youtrack():
    pass

@youtrack.command()
@click.option('-u', '--url', prompt="Enter in your Youtrack server")
@click.option('-n', '--username', prompt="Enter in your YouTrack username")
@click.option('-p', '--password', prompt="Enter in your YouTrack password")
@click.argument('from_date_string', nargs=1)
@click.argument('to_date_string', nargs=1)
def report(url, username, password, from_date_string, to_date_string):
    try:
        from_date = date_parse(from_date_string)
        to_date = date_parse(to_date_string)
    except:
        exit("Could not convert one or more date strings. Please use a recognised format such as YYYY-MM-DD")

    #get connection to youtrack
    connection = get_connection(url, username, password)
    #get project ids and loop through them
    project_ids = connection.getProjectIds()
    projects = []
    filter_string = "updated: " + from_date.strftime("%Y-%m-%d") + " .. " + to_date.strftime("%Y-%m-%d")
    report_items = []
    for id in project_ids:
        try:
            issues = connection.getIssues(id, filter_string, 0, 9999)
        except yt.YouTrackException as e:
            print("Cannot read issues for project " + id)
            continue
        for issue in issues:
            work_items = connection.getWorkItems(issue.id)
            for item in work_items:
                if item.authorLogin == username:
                    report_items.append(item)
    report_items.sort(key=lambda work_item: work_item.date)
    previous_date = None
    for item in report_items:
        item_date = datetime.datetime.utcfromtimestamp(int(item.date)/1000)
        current_date = item_date.strftime("%Y-%m-%d")
        if not current_date == previous_date:
            print("\n\n")
            print(current_date)
            previous_date = current_date
        url_parts = item.url.split('/')
        issue = "Unknown"
        for i in range(0, len(url_parts)):
            if url_parts[i] == "issue":
                issue = url_parts[i+1]
                break
        message = [
            item_date.strftime("%H:%M"),
            issue,
            str(datetime.timedelta(minutes=int(item.duration)))
        ]
        print("  " + " - ".join(message))




@youtrack.command()
@click.option('-u', '--url', prompt="Enter in your Youtrack server")
@click.option('-n', '--username', prompt="Enter in your YouTrack username")
@click.option('-p', '--password', prompt="Enter in your YouTrack password")
@click.argument('filename', type=click.File('rU', 'utf-8-sig'))
def manictime(url, username, password, filename):

    connection = get_connection(url, username, password)

    try:
        # u = filename.decode('utf-8-sig')
        # filename = u.encode('utf-8')
        rows = csv.DictReader(filename)
        print("Importing timeslips")
    except csv.Error as e:
        exit("Cound not find file")

    count = 0
    total = 0
    for row in rows:
        total += 1
        row = ManicTimeRow(connection, row)
        ignore = False

        if re.search('ignore', row.get_tags(), re.IGNORECASE):
            ignore = True
        else:
            first = True
            while True:
                # if we have issue id and issue exists break
                if row.issue_exists():
                    break
                else:
                    # if first time inform user what is going on
                    if first:
                        first = False
                        response = input("  No Issue found for \"" + row.get_tags() + "\". Add to an issue? (y/n): ")
                        if response.strip() == "n":
                            ignore = True
                            break
                    # if no project is set prompt user to choose one.
                    if not row.project_exists():
                        message = "  Enter Project Id or Project Name for " + row.timeslip_string()
                        message += " (Leave blank to skip this timeslip): "
                        project = input(message)
                        if project == "":
                            ignore = True
                            break
                    else:
                        message = "  Enter Issue Id or Search Terms for " + row.timeslip_string()
                        message += " (Leave blank to skip this timeslip): "
                        issue = input(message)
                        if issue == "":
                            ignore = True
                            break
                        results = row.search_issue(issue)
                        if results.length > 1:
                            pass
                        elif results.length == 1:
                            issue = results[0]
                            correctIssue = input("    Found issue " + issue.ID)
                        else:
                            print("    No issue found with entered search: " + results + ". Please try again.")

        if not ignore:
            if not row.timeslip_exists():
                    count += 1
                    # row.save()
                    print("    uploaded timeslip")
            else:
                print("  Timeslip for " + row.get_issue_id() + " (" +
                                 row.timeslip_string() + ") already exists")
        else:
            print("  Timeslip ignored")

    print("Added " + str(count) + " timeslips out of " + str(total))
    print("")


def get_connection(url, username, password):
    try:
        return Connection(url, username, password)
    except yt.YouTrackException as e:
        exit("Could not connect to YouTrack")


if __name__ == "__main__":
    youtrack()