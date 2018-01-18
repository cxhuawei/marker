from marker.cli import cliutils


class TargetCommands(object):
    """set of commands that allow you to manage targets

    """

    @cliutils.args("--target", dest="target", type=str)
    def add(self, api, target):
        if target:
            target = target.split(",")
        api.add(target)

    def delete(self, api, target):
        if target:
            target = target.split(",")
        api.delete(target)

    def start(self, api, target=None):
        if target:
            target = target.split(",")
        api.start(target)

    def stop(self, api, target=None):
        if target:
            target = target.split(",")
        api.stop(target)

    def list(self, api, task=None):
        api.list(task)
