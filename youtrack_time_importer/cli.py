from configparser import NoOptionError
from youtrack.connection import Connection
import configparser
import os
from dateutil.parser import parse as date_parse
from parsedatetime import Calendar
import click
from youtrack_time_importer.source import ToggleCSVSource, ToggleAPISource, ManictimeSource
from youtrack_time_importer.importer import Importer
from youtrack_time_importer.logger import ClickLogger
from youtrack_time_importer.date_range_enum import DateRangeEnum
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
@click.option('-t', '--test', is_flag=True)
@click.pass_context
def youtrack(ctx, url, username, password, test):
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
    ctx.obj['test'] = test

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
@click.argument('file', type=click.File('rU', 'utf-8-sig'))
@click.pass_context
def manictime(ctx, file):

    logger = ClickLogger(ctx)
    connection = ctx.obj['create_connection'].create()
    source = ManictimeSource(file)
    importer = Importer(connection, source, logger)
    importer.test = ctx.obj['test']
    importer.run()
    importer.results()


@youtrack.command()
@click.argument('file', type=click.File('rU', 'utf-8-sig'), required=False)
@click.option('-s', '--since', type=click.STRING, default=DateRangeEnum.yesterday.until().format("%Y-%m-%d"))
@click.option('-u', '--until', type=click.STRING, default=DateRangeEnum.yesterday.until().format("%Y-%m-%d"))
@click.option('-r', '--range', 'date_range', type=click.Choice([name for name, member in DateRangeEnum.__members__.items()]))
@click.pass_context
def toggl(ctx, file, since, until, date_range):

    logger = ClickLogger(ctx)
    connection = ctx.obj['create_connection'].create()

    if file:
        source = ToggleCSVSource(file)
    else:
        try:
            token = ctx.obj['cfg'].get('toggl', 'token')
            workspace_id = ctx.obj['cfg'].get('toggl', 'workspace')
        except NoOptionError as e:
            ctx.fail("No configuration set for connection to Toggl. "
                     "Please add your api token and workspace id to the config by using the following commands:\n\n"
                     "youtrack config add toggl.token <api_token>\n"
                     "youtrack config add toggl.workspace <workspace_id>\n")
        else:
            source = ToggleAPISource(token, workspace_id)
            if date_range:
                times = [member for name, member in DateRangeEnum.__members__.items() if name == date_range]
                source.start = times[0].since()
                source.end = times[0].until()
            else:
                try:
                    source.end = until
                except TypeError:
                    ctx.fail("Could not create a date from --until option: {0}".format(until))

                try:
                    source.start = since
                except TypeError:
                    ctx.fail("Could not create a date from --since option: {0}".format(since))

    importer = Importer(connection, source, logger)
    importer.test = ctx.obj['test']
    importer.run()
    importer.results()


if __name__ == "__main__":
    youtrack()