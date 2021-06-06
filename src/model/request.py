from datetime import datetime


class Request:
    def __init__(self, request: str):
        self._remotehost, self._rfc931, self._authuser, self._timestamp,\
            self._request, self.status, self._bytes = request.split(',')
        self._timestamp = int(self._timestamp)
        self.section = self._request.split(' ')[1].split('/')[1]
        self.date = datetime.utcfromtimestamp(self._timestamp).strftime('%Y-%m-%d %H:%M:%S')



