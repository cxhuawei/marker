import json
import os
import SocketServer
<<<<<<< HEAD

from marker.common import logging
from marker.server import daemon
from marker.server import utils
from marker.task.engine import TaskEngine
from oslo_config import cfg


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class ServiceEngine(object):

    @classmethod
    def start(cls):
        HOST = CONF.get("host")
        PORT = CONF.get("port")
        LOG.info("marker start service on {0}:{1}".format(HOST, PORT))
        try:
            server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)
        except Exception as e:
            LOG.error(e)
            return 1
        daemon_context = daemon.DaemonContext()
        daemon_context.files_preserve = [server.fileno(), cfg]
        with daemon_context:
            server.serve_forever()

    @classmethod
    def stop(cls, targets):
        HOST = CONF.get("host")
        for target in targets:
            utils.send("exit", target)
        utils.send("exit", HOST)


class MyTCPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        logging.setup("marker")
        self.data = self.request.recv(1024).strip()
        command = json.loads(self.data)
        action = command.get("action", None)
        data = command.get("data", None)
        target = command.get("target", None)
        source_ip = self.client_address[0]
        if action == "data":
            TaskEngine.upload_data(source_ip, data[0])
        elif action == "start":
            TaskEngine.run("start", data, source_ip, target)
        elif action == "stop":
            TaskEngine.run("stop", data, source_ip, target)
        elif action == "comfirm":
            LOG.info(data)
        elif action == "exit":
            TaskEngine.run("stop", data, source_ip, target)
            LOG.info("marker service stop on {0}".format(target))
            os._exit(os.EX_OK)
