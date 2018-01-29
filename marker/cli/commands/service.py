class ServiceCommands(object):
    """set of commands that allow you to start/stop marker
    service

    """

    def start(self, api):
        api.service.start()

    def stop(self, api):
        api.service.stop()
