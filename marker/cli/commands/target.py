from marker.cli import cliutils


class TargetCommands(object):
    """set of commands that allow you to manage targets

    """

    @cliutils.args("--target", dest="target", type="str")
    def add(api, target):
        if target:
            target = target.split(",")
        api.target.add(target)

    def delete(api, target):
        if target:
            target = target.split(",")
        api.target.delete(target)

    def start(api, target=None):
        if target:
            target = target.split(",")
        api.target.start(target)

    def stop(api, target=None):
        if target:
            target = target.split(",")
        api.target.stop(target)

    def list(api, task=None):
        api.target.list(task)
