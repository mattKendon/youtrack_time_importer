__author__ = 'Matthew'
import json
import sys, os
import click
from dateutil.parser import parse as date_parse
import datetime
from youtrack.connection import Connection
import csv
import youtrack as yt
from manictime import ManicTimeRow
from manictime import TogglRow
import configparser


def config_path():
    path = click.get_app_dir("YouTrack")
    if not os.path.exists(path):
        os.mkdir(path)
    return os.path.join(click.get_app_dir("YouTrack"), 'config.ini')


def read_config():
    try:
        cfg = config_path()
        parser = configparser.ConfigParser()
        parser.read([cfg])
        return parser
    except configparser.Error as e:
        exit(e.message)


@click.group()
@click.option('-u', '--url')
@click.option('-n', '--username')
@click.option('-p', '--password')
@click.pass_context
def youtrack(ctx, url, username, password):
    """ adds config file to Context and starts connection

    This will only start the connection if the subcommand is not config
    :param ctx:
    :return:
    """
    ctx.obj = dict()
    cfg = read_config()
    ctx.obj['config'] = cfg
    if not ctx.invoked_subcommand == 'config':
        if not (url and username) \
                and not (cfg.has_option('connection', 'url')
                         or cfg.has_option('connection', 'username')):
            click.echo("No configuration set for connection to YouTrack. "
                       "Please add your url and username to the config by using the following commands:")
            click.echo()
            click.echo("youtrack config add connection.username <username>")
            click.echo("youtrack config add connection.url <url>")
            click.echo()
            ctx.exit(-1)
        if not password:
            password = click.prompt("Please enter the password for the YouTrack user {0}".format(username), hide_input=True)
        try:
            connection = Connection(url, username, password)
            ctx.obj['connection'] = connection
        except yt.YouTrackException as e:
            ctx.fail(e)


@youtrack.group(invoke_without_command=True)
@click.pass_context
def config(ctx):
    """view command for config if no subcommand called"""
    if not ctx.invoked_subcommand:
        cfg = ctx.obj['config']
        for section in cfg.sections():
            print("[", section, "]")
            for option in cfg[section]:
                print(option, " = ", cfg[section][option])


@config.command()
@click.argument('option', nargs=1)
@click.argument('value', nargs=1)
@click.pass_context
def add(ctx, option, value):
    """command to add or update a parameter in the config

    Keyword arguments:
    option -- should include section with dot notation (eg. section.option)
    value -- the value of the option
    """
    properties = option.split(".")
    section = properties[0]
    option = properties[1]
    cfg = ctx.obj['config']
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, option, value)
    with open(config_path(), 'w') as fp:
        cfg.write(fp)


@youtrack.command()
@click.argument('name', nargs=1)
@click.argument('from_date_string', nargs=1)
@click.argument('to_date_string', nargs=1)
@click.pass_context
def report(ctx, name, from_date_string, to_date_string):

    try:
        from_date_string = date_parse(from_date_string).strftime("%Y-%m-%d")
        to_date_string = date_parse(to_date_string).strftime("%Y-%m-%d")
    except:
        ctx.fail("Could not convert one or more date strings. "
                 "Please use a recognised format such as YYYY-MM-DD")

    #get connection to youtrack
    connection = ctx.obj['connection']

    #filter string
    filter_string = ""

    #get project ids and loop through them
    project_ids = connection.getProjectIds()
    report_items = []
    click.echo("Searching {0} projects for tasks that you've worked on".format(len(project_ids)))
    with click.progressbar(project_ids) as bar:
        for project_id in bar:
            try:
                issues = connection.getIssues(project_id, filter_string, 0, 9999)
            except yt.YouTrackException as e:
                continue
            for issue in issues:
                work_items = connection.getWorkItems(issue.id)
                for item in work_items:
                    item_date_string = datetime.datetime.utcfromtimestamp(int(item.date)/1000).strftime("%Y-%m-%d")
                    if item.authorLogin == name \
                            and from_date_string <= item_date_string <= to_date_string:
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
@click.argument('filename', type=click.File('rU', 'utf-8-sig'))
def manictime(url, username, password, filename):

    url = get_url(url)
    username = get_username(username)
    password = get_password(password)
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
                row.save()
                print("    uploaded timeslip")
            else:
                print("  Timeslip for " + row.get_issue_id() + " (" +
                      row.timeslip_string() + ") already exists")
        else:
            # ignore
            print("  Timeslip ignored")
    print("Added " + str(count) + " timeslips out of " + str(total))


@youtrack.command()
@click.argument('filename', type=click.File('rU', 'utf-8-sig'))
def toggl(url, username, password, filename):

    url = get_url(url)
    username = get_username(username)
    password = get_password(password)
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
        row = TogglRow(connection, row)
        if process_row(row):
            # save
            if not row.timeslip_exists():
                count += 1
                row.save()
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
                print("    Could not find issue with id of " + issue_id + ". Please try again.")
                continue
    # if we ever get to ignore Row
    return False


def get_setting(setting):
    configFile = extract_config()
    properties = setting.split(".")
    section = properties[0]
    option = properties[1]
    if section in configFile.sections():
        if option in configFile[section]:
            return configFile[section][option]
    return False


def get_url(url):
    if not url:
        url = get_setting('connection.url')
        if not url:
            url = input("Enter in your Youtrack server: ")
    return url


def get_username(username):
    if not username:
        username = get_setting('connection.user')
        if not username:
            username = input("Enter in your YouTrack username: ")
    return username


def get_password(password):
    if not password:
        password = input("Enter in your YouTrack password: ")
    return password


def get_connection(url, username, password):
    try:
        return Connection(url, username, password)
    except yt.YouTrackException as e:
        exit("Could not connect to YouTrack")


if __name__ == "__main__":
    youtrack()