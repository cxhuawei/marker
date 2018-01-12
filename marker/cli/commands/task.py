class TaskCommands(object):
    """set of commands that allow you to manage task

    """

    def add(api, task, target=None):
        api.task.add(task, target)

    def delete(api, task, target=None):
        api.task.delete(task, target)

    def start(api, task):
        api.task.start(task)

    def stop(api, task):
        api.task.stop(task)

    def list(api, target=None):
        api.task.list(target)
