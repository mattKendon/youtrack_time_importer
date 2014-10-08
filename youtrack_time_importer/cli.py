__author__ = 'Matthew'

from configparser import NoOptionError
from dateutil.parser import parse as date_parse
from parsedatetime import Calendar
from requests.exceptions import ConnectionError
from youtrack.connection import Connection
from youtrack_time_importer.row import TogglCSVRow
from youtrack_time_importer.row import TogglAPIRow
from youtrack_time_importer.row import YoutrackIssueNotFoundException
from youtrack_time_importer.row import YoutrackMissingConnectionException
from youtrack_time_importer.row import YoutrackWorkItemIncorrectException
import click
import configparser
import csv
import datetime
import json
import os
import requests
import youtrack as yt


yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')


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

    class CreateConnection(object):
        def __init__(self, url, username, password, cfg):
            if not url:
                url = cfg.get('connection', 'url')
            if not username:
                username = cfg.get('connection', 'username')
            self.url = url
            self.username = username
            self.password = password

        def create(self):
            if not self.password:
                message = "Please enter the password for the YouTrack user {0}".format(self.username)
                self.password = click.prompt(message, hide_input=True)
            return Connection(self.url, self.username, self.password)


    ctx.obj = dict()
    cfg = read_config()
    ctx.obj['cfg'] = cfg

    try:
        ctx.obj['create_connection'] = CreateConnection(url, username, password, cfg)
    except NoOptionError as e:
        ctx.fail("No configuration set for connection to YouTrack. "
                   "Please add your url and username to the config by using the following commands:\n\n"
                   "youtrack config add connection.username <username>\n"
                   "youtrack config add connection.url <url>\n")


@youtrack.group(invoke_without_command=True)
@click.pass_context
def config(ctx):
    """view command for config if no subcommand called"""
    if not ctx.invoked_subcommand:
        cfg = ctx.obj['cfg']
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
    cfg = ctx.obj['cfg']
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
    pass


@youtrack.command()
@click.argument('filename', type=click.File('rU', 'utf-8-sig'))
@click.option('-t', '--testing', is_flag=True)
@click.pass_context
def manictime(ctx, filename, testing):
    pass



@youtrack.command()
@click.argument('file', type=click.File('rU', 'utf-8-sig'), required=False)
@click.option('-t', '--testing', is_flag=True)
@click.option('-s', '--since', type=click.STRING, default=yesterday)
@click.option('-u', '--until', type=click.STRING, default=yesterday)
@click.pass_context
def toggl(ctx, file, since, until, testing):

    try:
        connection = ctx.obj['create_connection'].create()
    except yt.YouTrackException as e:
        ctx.fail(e)

    rows = list()

    if file:
        row_class = TogglCSVRow
        try:
            rows = csv.DictReader(file)
        except csv.Error as e:
            ctx.fail("Could not find file")
    else:
        row_class = TogglAPIRow
        params = dict()
        url = "https://toggl.com/reports/api/v2/details"
        params['user_agent'] = "matt@outlandish.com"
        try:
            token = ctx.obj['cfg'].get('toggl', 'token')
            workspace_id = ctx.obj['cfg'].get('toggl', 'workspace')
        except NoOptionError as e:
            ctx.fail("No configuration set for connection to Toggl. "
                   "Please add your api token and workspace id to the config by using the following commands:\n\n"
                   "youtrack config add toggl.token <api_token>\n"
                   "youtrack config add toggl.workspace <workspace_id>\n")
        else:
            auth = (token, "api_token")
            params['workspace_id'] = workspace_id

            try:
                params['since'] = process_datetime(since)
            except TypeError:
                ctx.fail("Could not create a date from --since option: {0}".format(since))

            try:
                params['until'] = process_datetime(until)
            except TypeError:
                ctx.fail("Could not create a date from --until option: {0}".format(until))

            try:
                result = requests.get(url, auth=auth, params=params)
            except requests.ConnectionError as e:
                ctx.fail("Could not connect to Toggl. Error: {0}".format(e))
            else:
                rows = result.json()['data']

    for row in rows:
        row = row_class(row, connection)
        if row.is_ignored():
            click.echo("\nIgnored: Time Entry for {0}".format(row.__str__()))
            continue
        while True:
            if row.work_item_exists():
                click.echo("\nDuplicate: Time Entry for {0}".format(row.__str__()))
                break
            try:
                row.save_work_item()
            except YoutrackIssueNotFoundException as e:
                click.echo("Could not upload Time Entry for {0}".format(row.__str__()))
                click.echo("  Error: No Issue found or Issue Id incorrect\n")
                issue_id = click.prompt("  Please provide the correct Issue Id [leave blank to ignore]:")
                if not issue_id:
                    click.echo("\nIgnored: Time Entry for {0}".format(row.__str__()))
                    break
                row.issue_id = issue_id
            except YoutrackMissingConnectionException as e:
                click.echo("Could not upload Time Entry for {0}".format(row.__str__()))
                ctx.fail("  Error: YouTrack connection is missing method to create Time Entry")
            except yt.YouTrackException as e:
                click.echo("Could not upload Time Entry for {0}".format(row.__str__()))
                ctx.fail("  Error: Unable to connect to YouTrack")
            except YoutrackWorkItemIncorrectException as e:
                click.echo("Could not upload Time Entry for {0}".format(row.__str__()))
                ctx.fail("  Error: Unable to create Time Entry. Missing important properties")
            else:
                click.echo("\nCreated: Time Entry for {0}".format(row.__str__()))
                break


def process_datetime(date_string):
    cal = Calendar()
    try:
        dt = date_parse(date_string)
    except TypeError:
        dt = cal.nlp(date_string)[0][0]
    return dt




def process_row(row):
    # if ignore exists in tags, return False
    if row.is_ignored():
        return False
    # if issue exists and we haven't ignored it
    if row.issue_exists():
        return True
    # if issue does not exist lets prompt the user
    response = click.confirm("  No Issue found for \"{0}\". Add to an issue?".format(row.get_issue_string()))
    # if they respond "n" return False
    if not response:
        return False
    # if they want to go ahead start loop
    while True:
        # check to see if issue exists
        if row.issue_exists():
            return True
        # lets get a project from them
        if not row.project_exists():
            message = "  Enter Project Id for {0} (Leave blank to skip this timeslip)"
            project_id = click.prompt(message.format(row.timeslip_string()))
            # if left blank, ignore row
            if project_id == "":
                return False
            # get the project from Youtrack
            try:
                project = row.connection.getProject(project_id)
                if isinstance(project, yt.Project):
                    row.project = project
                    continue
            except yt.YouTrackException as e:
                pass
            click.echo("    Could not find project with {0}. Please try again.".format(project_id))
            continue
        # if we have a project lets try get an issue
        else:
            message = "  Enter Issue Id for {0} (Leave blank to skip this timeslip)"
            issue_id = click.prompt(message.format(row.timeslip_string()))
            # if left blank ignore row
            if issue_id == "":
                return False
            # get the issue from Youtrack
            try:
                issue = row.connection.get_issue(issue_id)
                if isinstance(issue, yt.Issue):
                    row.issue = issue
                    continue
            except yt.YouTrackException as e:
                click.echo(e)
            click.echo("    Could not find issue with id of {0}. Please try again.".format(issue_id))
            continue
    # if we ever get to ignore Row
    return False


if __name__ == "__main__":
    youtrack()