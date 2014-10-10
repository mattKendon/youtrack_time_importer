__author__ = 'Matthew'

from configparser import NoOptionError
from dateutil.parser import parse as date_parse
from parsedatetime import Calendar
from youtrack.connection import Connection
from youtrack_time_importer.row import TogglCSVRow
from youtrack_time_importer.row import TogglAPIRow
from youtrack_time_importer.row import ManictimeRow
from youtrack_time_importer.row import YoutrackIssueNotFoundException
from youtrack_time_importer.row import YoutrackMissingConnectionException
from youtrack_time_importer.row import YoutrackWorkItemIncorrectException
from youtrack_time_importer.date_range_enum import DateRangeEnum
import click
import configparser
import csv
import json
import os
import requests
import youtrack as yt


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
    """ adds config file and Connection creating object to ctx

    This will prepare the context for other commands. It reads the config file
    and adds the file to the Context. It also instantiates the CreateConnection class
    which allows for lazy loading of the Youtrack connection so that we only try to
    connect if we are required to.
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

    if 'config' != ctx.invoked_subcommand:
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
    click.echo("Coming Soon!")
    exit()


@youtrack.command()
@click.argument('file', type=click.File('rU', 'utf-8-sig'))
@click.pass_context
def manictime(ctx, file):

    row_class = ManictimeRow
    try:
        rows = csv.DictReader(file)
    except csv.Error as e:
        ctx.fail("Could not find file")
    else:
        process_rows(list(rows), row_class, ctx)



@youtrack.command()
@click.argument('file', type=click.File('rU', 'utf-8-sig'), required=False)
@click.option('-s', '--since', type=click.STRING, default=DateRangeEnum.yesterday.until().format("%Y-%m-%d"))
@click.option('-u', '--until', type=click.STRING, default=DateRangeEnum.yesterday.until().format("%Y-%m-%d"))
@click.option('-r', '--range', type=click.Choice([name for name, member in DateRangeEnum.__members__.items()]))
@click.pass_context
def toggl(ctx, file, since, until, range):

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

            if range:
                times = [member for name, member in DateRangeEnum.__members__.items() if name == range]
                params['since'] = times[0].since()
                params['until'] = times[0].until()
            else:
                try:
                    params['until'] = process_datetime(until)
                except TypeError:
                    ctx.fail("Could not create a date from --until option: {0}".format(until))

                try:
                    params['since'] = process_datetime(since)
                except TypeError:
                    ctx.fail("Could not create a date from --since option: {0}".format(since))

            try:
                result = requests.get(url, auth=auth, params=params)
            except requests.ConnectionError as e:
                ctx.fail("Could not connect to Toggl. Error: {0}".format(e))
            else:
                rows = result.json()['data']

    process_rows(rows, row_class, ctx)

    if len(row_class.ids) and row_class == TogglAPIRow:
        ids = [str(id) for id in row_class.ids]
        url = "https://www.toggl.com/api/v8/time_entries/{0}".format(",".join(ids))
        data = {"time_entry": {"tags": ["youtracked"], "tag_action": "add"}}
        try:
            requests.put(url, auth=auth, data=json.dumps(data))
        except requests.ConnectionError as e:
            ctx.fail("Could not update Toggl: {0}".format(e))


def process_datetime(date_string):
    cal = Calendar()
    try:
        dt = date_parse(date_string)
    except TypeError:
        dt = cal.nlp(date_string)[0][0]
    return dt


def process_rows(rows, row_class, ctx):

    try:
        connection = ctx.obj['create_connection'].create()
    except yt.YouTrackException as e:
        ctx.fail(e)
    else:
        try:
            total = len(rows)
        except TypeError as e:
            click.echo("Could not get total number of rows.")
            total = 0
        ignored = 0
        created = 0
        duplicate = 0
        error = 0

        click.echo("\nProcessing {0} time entries. Please wait\n".format(total))

        for row in rows:
            row = row_class(row, connection)
            if row.is_ignored():
                click.echo("Ignored: Time Entry for {0}\n".format(row.__str__()))
                ignored += 1
                continue
            while True:
                if row.work_item_exists():
                    click.echo("Duplicate: Time Entry for {0}\n".format(row.__str__()))
                    duplicate += 1
                    break
                try:
                    row.save_work_item()
                except YoutrackIssueNotFoundException as e:
                    click.echo("Could not upload Time Entry for {0}".format(row.__str__()))
                    click.echo("  Error: No Issue found or Issue Id incorrect\n")
                    issue_id = click.prompt("  Please provide the correct Issue Id [leave blank to ignore]:")
                    if not issue_id:
                        click.echo("Ignored: Time Entry for {0}\n".format(row.__str__()))
                        ignored += 1
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
                    click.echo("  Error: Unable to create Time Entry. Missing important properties\n")
                    error += 1
                    break
                else:
                    click.echo("Created: Time Entry for {0}\n".format(row.__str__()))
                    created += 1
                    break
        click.echo("Processed {0} time entries.".format(total))
        click.echo("  Ignored: {0}.".format(ignored))
        click.echo("  Error: {0}.".format(error))
        click.echo("  Duplicate: {0}.".format(duplicate))
        click.echo("  Created: {0}.".format(created))

if __name__ == "__main__":
    youtrack()