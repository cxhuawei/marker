from marker.cli import cliutils


class ServiceCommands(object):
    """set of commands that allow you to start/stop marker
    service

    """

    @cliutils.args("--ip", dest="ip", type=str)
    def start(self, api, ip):
        api.service.start(ip)

    def stop(self, api):
        api.service.stop()
