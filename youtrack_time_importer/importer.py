from youtrack import YouTrackException

from youtrack_time_importer import row


class Importer():

    def __init__(self, connection, source, logger):
        self.connection = connection
        self.source = source
        self.logger = logger
        self.ignored = 0
        self.created = 0
        self.failed = 0
        self.duplicate = 0
        self.test = False

    def work_item_exists(self, source_row):
        """Checks to see if WorkItem already exists

        Gets all the WorkItems for an issue and checks to see if
        once exists with the same date and duration. As date is a timestamp
        based on date and time, this should be completely unique.

        Args:
            row: A Row object provided self.source

        Returns:
            Boolean value, returning True if it exists, and false if :
            it doesn't

        Raises:
            A YoutrackIssueNotFoundException if issue doesnt exist on server
        """

        try:
            work_items = self.connection.getWorkItems(source_row.issue_id)
        except YouTrackException as e:
            return False
        else:
            for work_item in work_items:
                if (work_item.authorLogin == self.connection.login and
                        work_item.date == source_row.work_item.date and
                        work_item.duration == source_row.work_item.duration):
                    return True
            return False

    def save_work_item(self, source_row):
        """Saves WorkItem to Youtrack

        Uses the Youtrack Connection to save the WorkItem
        to the issue, if it is determined that the issue ID
        is correct.

        Args:
            row: A Row object provided by self.source

        Raises:
            A YoutrackMissingConnectionException if the connection object
            doesnt' have the method createWorkItem()
            a YoutrackIssueNotFoundException if issue doesnt exist on server,
            a YoutrackWorkItemIncorrectException if the work_item does not have
            all attributes
        """

        if self.test:
            return

        try:
            self.connection.createWorkItem(source_row.issue_id, source_row.work_item)
        except AttributeError as ae:
            if "createWorkItem" in ae.args[0]:
                raise row.YoutrackMissingConnectionException()
            else:
                raise row.YoutrackWorkItemIncorrectException()
        except YouTrackException as e:
            raise row.YoutrackIssueNotFoundException

    def run(self):
        for source_row in self.source:
            if source_row.is_ignored():
                self.ignored += 1
                self.logger.message("Ignored: Time Entry for {0}\n".format(source_row.__str__()))
                continue
            while True:
                if self.work_item_exists(source_row):
                    self.logger.message("Duplicate: Time Entry for {0}\n".format(source_row.__str__()))
                    self.duplicate += 1
                    break
                try:
                    self.save_work_item(source_row)
                except row.YoutrackIssueNotFoundException as e:
                    self.logger.message("Could not upload Time Entry for {0}".format(source_row.__str__()))
                    self.logger.message("  Error: No Issue found or Issue Id incorrect\n")
                    issue_id = self.logger.prompt("  Please provide the correct Issue Id [leave blank to ignore]:")
                    if not issue_id:
                        self.logger.message("Ignored: Time Entry for {0}\n".format(source_row.__str__()))
                        self.ignored += 1
                        break
                    row.issue_id = issue_id
                except row.YoutrackMissingConnectionException as e:
                    self.logger.message("Could not upload Time Entry for {0}".format(source_row.__str__()))
                    self.logger.fail("  Error: YouTrack connection is missing method to create Time Entry")
                except YouTrackException as e:
                    self.logger.message("Could not upload Time Entry for {0}".format(source_row.__str__()))
                    self.logger.fail("  Error: Unable to connect to YouTrack")
                except row.YoutrackWorkItemIncorrectException as e:
                    self.logger.message("Could not upload Time Entry for {0}".format(source_row.__str__()))
                    self.logger.message("  Error: Unable to create Time Entry. Missing important properties\n")
                    self.failed += 1
                    break
                else:
                    self.logger.message("Created: Time Entry for {0}\n".format(source_row.__str__()))
                    self.created += 1
                    break

    def results(self):
        self.logger.message("Processed {0} time entries.".format(len(self.source)))
        self.logger.message("  Ignored: {0}.".format(self.ignored))
        self.logger.message("  Error: {0}.".format(self.failed))
        self.logger.message("  Duplicate: {0}.".format(self.duplicate))
        self.logger.message("  Created: {0}.".format(self.created))