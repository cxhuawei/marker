class TaskCommands(object):
    """set of commands that allow you to manage task

    """

    def add(self, api, task, target=None):
        api.task.add(task, target)

    def delete(self, api, task, target=None):
        api.task.delete(task, target)

    def start(self, api, task):
        api.task.start(task)

    def stop(self, api, task):
        api.task.stop(task)

    def list(self, api, target=None):
        api.task.list(target)
