import ConfigParser
import json
import os
import SocketServer

from marker.common import logging
from marker.server import daemon
from marker.server import utils
from marker.task.engine import TaskEngine
from oslo_config import cfg


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class ServiceEngine(object):

    @classmethod
    def start(cls, ip, config_files):
        if ip and ":" in ip:
            HOST = ip.split(":")[0]
            PORT = int(ip.split(":")[1])
        elif ip:
            HOST = ip
            PORT = CONF.get("port")
        else:
            HOST = CONF.get("host")
            PORT = CONF.get("port")
        conf = ConfigParser.ConfigParser()
        conf.read(config_files[0])
        conf.set("DEFAULT", "host", HOST)
        conf.set("DEFAULT", "port", PORT)
        with open(config_files[0], "w") as f:
            conf.write(f)
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
        PORT = CONF.get("port")
        for target in targets:
            utils.send("exit", target)
        utils.send("exit", HOST, port=PORT)


class MyTCPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        logging.setup("marker")
        self.data = self.request.recv(1024).strip()
        command = json.loads(self.data)
        action = command.get("action", None)
        data = command.get("data", {})
        target = command.get("target", None)
        source_ip = self.client_address[0]
        LOG.info("option: receive. \ncommand: {0}. \naction: {1}. \n"
                 "data: {2}. \ntarget: {3}. \nsource_ip: {4}.".format(
                     str(command), str(action), str(data), str(target),
                     str(source_ip)))
        if action == "data":
            TaskEngine.upload_data(source_ip, data)
        elif action in ["start", "stop"]:
            task_list = data.get("context")
            role = data.get("role", "client")
            addition = data.get("addition")
            TaskEngine.run(action, task_list, source_ip,
                           target, role=role, addition=addition)
        elif action == "comfirm":
            comfirm_type = data.get("type")
            task = data.get("task")
            step = data.get("step")
            role = data.get("role")
            status = data.get("status")
            if comfirm_type == "start" and role == "client":
                TaskEngine.check_db(source_ip, task, step)
                LOG.info("Task {0} {1} on target {2}".format(
                    task, comfirm_type, source_ip))
            if role == "server" and status == "failed":
                client_ip = data.get("client_ip")
                utils.send("stop", client_ip,
                           data={"context": [task], "role": "client"})
        elif action == "exit":
            TaskEngine.run("stop", data, source_ip, target, role="server")
            TaskEngine.run("stop", data, source_ip, target, role="client")
            LOG.info("marker service stop on {0}".format(target))
            os._exit(os.EX_OK)
