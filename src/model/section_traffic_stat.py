from src.model.request import Request


class SectionTrafficStats:
    def __init__(self, section: str):
        self.hits_by_status = {}
        self.section = section
        self.total_hits = 0

    def add_request(self, request: Request):
        self.hits_by_status.setdefault(request.status, 0)
        self.hits_by_status[request.status] += 1
        self.total_hits += 1

    def __lt__(self, other):
        return self.total_hits > other.total_hits