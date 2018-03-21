import json
import os
import SocketServer
import socket

from marker.api import API
from marker.common import logging
from marker.server import daemon
from marker.task.engine import TaskEngine
from oslo_config import cfg


CONF = cfg.CONF
HOST_OPTS = [cfg.StrOpt(
    "host",
    default="localhost",
    help="specifies host of marker service.")]
PORT_OPTS = [cfg.IntOpt(
    "port",
    default=9999,
    help="specifies port of marker service.")]
CONF.register_opts(HOST_OPTS)
CONF.register_opts(PORT_OPTS)
HOST = CONF.get("host")
PORT = CONF.get("port")
LOG = logging.getLogger(__name__)


class ServiceEngine(object):

    @classmethod
    def start(cls):
        LOG.info("marker start service on {0}:{1}".format(HOST, PORT))
        try:
            server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)
        except Exception as e:
            LOG.error(e)
            return 1
        daemon_context = daemon.DaemonContext()
        daemon_context.files_preserve = [server.fileno()]
        with daemon_context:
            server.serve_forever()

    @classmethod
    def stop(cls):
        targets = API.target.list()
        for target in targets:
            cls.send("exit", target)
        cls.send("exit", HOST)

    @classmethod
    def send(cls, action, target, data=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((target, PORT))
        except Exception as e:
            LOG.warning(e)
            LOG.warning("There is no marker service on {0}:{1}".format(
                target, PORT))
            return 1
        sock.sendall(json.dumps({"action": action,
                                 "data": [data], "target": target}))
        sock.close()


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
            pass
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
