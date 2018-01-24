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

    def start(self, api, targets=None):
        if targets:
            targets = targets.split(",")
        api.target.start(targets)

    def stop(self, api, targets=None):
        if targets:
            targets = targets.split(",")
        api.target.stop(targets)

    @cliutils.args("--task", dest="task", type=str)
    def list(self, api, task=None):
        api.target.list(task)
