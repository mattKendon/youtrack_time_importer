__author__ = 'Matthew'
import click
from dateutil.parser import parse as date_parse
import datetime
from youtrack.connection import Connection
import csv
import re
import youtrack as yt
from manictime import ManicTimeRow


class Messages(object):
    pass

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
                item_date = datetime.datetime.utcfromtimestamp(int(item.date)/1000)
                if item.authorLogin == username \
                        and item_date.strftime("%Y-%m-%d") >= from_date.strftime("%Y-%m-%d") \
                        and item_date.strftime("%Y-%m-%d") <= to_date.strftime("%Y-%m-%d"):
                    report_items.append(item)
    report_items.sort(key=lambda work_item: work_item.date)
    previous_date = None
    for item in report_items:
        item_date = datetime.datetime.utcfromtimestamp(int(item.date)/1000)
        current_date = item_date.strftime("%Y-%m-%d")
        if not current_date == previous_date:
            print("\n")
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
        rows = csv.DictReader(filename)
        print("Importing timeslips")
    except csv.Error as e:
        exit("Could not find file")

    count = 0
    total = 0
    for row in rows:
        total += 1
        row = ManicTimeRow(connection, row)
        if process_row(row):
            # save
            if not row.timeslip_exists():
                count += 1
                # row.save()
                print("    uploaded timeslip")
            else:
                print("  Timeslip for " + row.get_issue_id() + " (" +
                      row.timeslip_string() + ") already exists")
        else:
            # ignore
            print("  Timeslip ignored")
    print("Added " + str(count) + " timeslips out of " + str(total))

def process_row(row):
    # if ignore exists in tags, return False
    if row.is_ignored():
        return False
    # if issue exists and we haven't ignored it
    if row.issue_exists():
        return True
    # if issue does not exist lets prompt the user
    response = input("  No Issue found for \"" + row.get_tags() + "\". Add to an issue? (y/n): ")
    # if they respond "n" return False
    if response.strip() == "n":
        return False
    # if they want to go ahead start loop
    while True:
        # check to see if issue exists
        if row.issue_exists():
            return True
        # lets get a project from them
        if not row.project_exists():
            message = "  Enter Project Id for " + row.timeslip_string()
            message += " (Leave blank to skip this timeslip): "
            project_id = input(message)
            # if left blank, ignore row
            if project_id == "":
                return False
            # get the project from Youtrack
            project = row.connection.getProject(project_id)
            # if we have a project set it and continue
            if isinstance(project, youtrack.Project):
                row.project = project
            # else tell the user and try again
            else:
                print("    Could not find project with " + project_id + ". Please try again.")
                continue
        # if we have a project lets try get an issue
        else:
            message = "  Enter Issue Id for " + row.timeslip_string()
            message += " (Leave blank to skip this timeslip): "
            issue_id = input(message)
            # if left blank ignore row
            if issue_id == "":
                return False
            # get the issue from Youtrack
            issue = row.connection.get_issue(issue_id)
            if isinstance(issue, youtrack.Issue):
                row.issue = issue
            else:
                print("    Count not fin isue with id of " + issue_id + ". Please try again.")
                continue
    # if we ever get to ignore Row
    return False

def get_connection(url, username, password):
    try:
        return Connection(url, username, password)
    except yt.YouTrackException as e:
        exit("Could not connect to YouTrack")


if __name__ == "__main__":
    youtrack()