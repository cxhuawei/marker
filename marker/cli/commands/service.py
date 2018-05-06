from marker.cli import cliutils


class ServiceCommands(object):
    """set of commands that allow you to start/stop marker
    service

    """

    @cliutils.args("--ip", dest="ip", type=str, required=False)
    def start(self, api, ip=None):
        api.service.start(ip)

    def stop(self, api):
        api.service.stop()
