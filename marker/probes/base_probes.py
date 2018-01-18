from marker.common.objects import targetandtask


class BaseProbes(object):

    def __init__(self, target):
        self.target = target
        self.data = None

    def run(self):
        pass

    def upload_data(self):
        targetandtask.upload_data(self.target, self.data)
