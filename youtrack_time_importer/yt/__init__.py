from youtrack import WorkItem as OldWorkItem


class WorkItem(OldWorkItem):

    @property
    def issue(self):
        parts = self.url.split('/')
        for id, val in enumerate(parts):
            if val == 'issue':
                return parts[id+1]
        return None