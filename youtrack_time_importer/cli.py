__author__ = 'Matthew'

import os
import click
from dateutil.parser import parse as date_parse
from youtrack_time_importer.yt.connection import Connection
import csv
import youtrack as yt
from youtrack_time_importer import ManicTimeRow
from youtrack_time_importer import TogglRow
import configparser
from configparser import NoOptionError
from requests.exceptions import ConnectionError
from youtrack_time_importer.report import Report


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

        try:
            if not url and cfg.has_option('connection', 'url'):
                url = cfg.get('connection', 'url')
            if not username and cfg.has_option('connection', 'url'):
                username = cfg.get('connection', 'username')
        except NoOptionError as e:
            url = None
            username = None

        if not url and not username:
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
        except ConnectionError as e:
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
        from_date = date_parse(from_date_string)
        to_date = date_parse(to_date_string)
    except Exception as e:
        ctx.fail("Could not convert one or more date strings. "
                 "Please use a recognised format such as YYYY-MM-DD")
    else:
        connection = ctx.obj['connection']
        report = Report(connection, name, from_date, to_date)

        report.print()



@youtrack.command()
@click.argument('filename', type=click.File('rU', 'utf-8-sig'))
@click.option('-t', '--testing', is_flag=True)
@click.pass_context
def manictime(ctx, filename, testing):

    connection = ctx.obj['connection']

    try:
        rows = csv.DictReader(filename)
        click.echo("Importing timeslips")
    except csv.Error as e:
        ctx.fail("Could not find file")

    count = 0
    total = 0
    for row in rows:
        total += 1
        row = ManicTimeRow(connection, row)
        if process_row(row):
            # save
            if not row.timeslip_exists():
                count += 1
                if not testing:
                    row.save()
                click.echo("  Uploaded timeslip for {0}".format(row.timeslip_string()))
            else:
                click.echo("  Timeslip for {0} ({1}) already exists".format(row.get_issue_id(), row.timeslip_string()))
        else:
            # ignore
            click.echo("  Timeslip ignored")
    click.echo("Added {0} timeslips out of {1}.".format(count, total))


@youtrack.command()
@click.argument('filename', type=click.File('rU', 'utf-8-sig'))
@click.option('-t', '--testing', is_flag=True)
@click.pass_context
def toggl(ctx, filename, testing):

    connection = ctx.obj['connection']

    try:
        rows = csv.DictReader(filename)
        click.echo("Importing timeslips")
    except csv.Error as e:
        ctx.fail("Could not find file")

    count = 0
    total = 0
    for row in rows:
        total += 1
        row = TogglRow(connection, row)
        if process_row(row):
            # save
            if not row.timeslip_exists():
                count += 1
                if not testing:
                    row.save()
                click.echo("  Uploaded timeslip for {0}".format(row.timeslip_string()))
            else:
                click.echo("  Timeslip for {0} ({1}) already exists".format(row.get_issue_id(), row.timeslip_string()))
        else:
            # ignore
            click.echo("  Timeslip ignored")
    click.echo("Added {0} timeslips out of {1}.".format(count, total))


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