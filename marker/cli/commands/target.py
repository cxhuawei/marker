from marker.cli import cliutils


class TargetCommands(object):
    """set of commands that allow you to manage targets

    """

    def add(self, api, target):
        if target:
            target = target.split(",")
        api.target.add(target)

    def delete(self, api, target):
        if target:
            target = target.split(",")
        api.target.delete(target)

    def start(self, api, target=None):
        if target:
            target = target.split(",")
        api.target.start(target)

    def stop(self, api, target=None):
        if target:
            target = target.split(",")
        api.target.stop(target)

    @cliutils.args("--task", dest="task", type=str)
    def list(self, api, task=None):
        api.target.list(task)
