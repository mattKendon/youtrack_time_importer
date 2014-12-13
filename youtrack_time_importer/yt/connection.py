from youtrack.connection import Connection as OldConnection
from youtrack.connection import minidom, Node
from youtrack import Issue, YouTrackException
from youtrack_time_importer.yt import WorkItem


class Connection(OldConnection):

    def __init__(self, url, login, password, proxy_info=None):
        self.login = login
        super().__init__(url, login, password, proxy_info)

    def get_issues(self, filter='', after='0', max='9999'):
        response = self._req('GET', '/issue/', params={'after': str(after),
                                                       'max': str(max),
                                                       'filter': str(filter)})
        xml = minidom.parseString(response.content)
        return [Issue(e, self) for e in xml.documentElement.childNodes if e.nodeType == Node.ELEMENT_NODE]

    def getWorkItems(self, issue_id):
        try:
            response = self._req('GET',
                '/issue/{0}/timetracking/workitem'.format(issue_id))
            xml = minidom.parseString(response.content)
            return [WorkItem(e, self) for e in xml.documentElement.childNodes if
                    e.nodeType == Node.ELEMENT_NODE]
        except YouTrackException as e:
            print("Can't get work items.", str(e))
            return []


