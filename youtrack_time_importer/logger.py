import abc
import click


class Logger(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def fail(self, message):
        pass

    @abc.abstractmethod
    def message(self, message):
        pass

    @abc.abstractmethod
    def prompt(self, message):
        pass


class ClickLogger(Logger):

    def __init__(self, ctx):
        self.ctx = ctx

    def fail(self, message):
        self.ctx.fail(message)

    def message(self, message):
        click.echo(message)

    def prompt(self, message):
        return click.prompt(message)