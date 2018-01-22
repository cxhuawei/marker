from marker.cli import cliutils


class TaskCommands(object):
    """set of commands that allow you to manage task

    """

    @cliutils.args("--target", dest="target", type=str)
    def add(self, api, task, target=None):
        api.task.add(task, target)

    @cliutils.args("--target", dest="target", type=str)
    def delete(self, api, task, target=None):
        api.task.delete(task, target)

    def start(self, api, task):
        api.task.start(task)

    def stop(self,api, task):
        api.task.stop(task)

    @cliutils.args("--target", dest="target", type=str)
    def list(self, api, target=None):
        api.task.list(target)
