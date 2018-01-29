import json
import os
import SocketServer
import socket
import time

from marker.common import logging
from marker.probes.base_probes import BaseProbes
from marker.task import daemon
from multiprocessing import Process
from multiprocessing import Queue
from oslo_config import cfg
from Queue import Empty
from threading import Thread

HOST = "localhost"
PORT = 9999
WAIT_TIMEOUT = 5
ACTIVE_TASK = {}
TARGET_TASK = []
QUEUE_DICT = {}

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

STEP_OPTS = [cfg.IntOpt(
    "step",
    default=5,
    help="specifies the base interval in seconds"
         " with which data will fed into the rrd.")]
CONF.register_opts(STEP_OPTS)


class ServiceEngine(object):

    @classmethod
    def start(cls):
        LOG.info("marker start on {0}:{1}".format(HOST, PORT))
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
        except Exception as e:
            LOG.warning(e)
            LOG.warning("There is no marker service on {0}:{1}".format(
                HOST, PORT))
            return 1
        sock.sendall(json.dumps({"marker": "exit"}))
        LOG.info("marker stop on {0}:{1}".format(HOST, PORT))
        sock.close()


class TaskEngine(object):

    @classmethod
    def run(cls, task_dict):
        cls._update_task(task_dict)

    @classmethod
    def _update_task(cls, task_dict):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
        except Exception as e:
            LOG.warning(e)
            LOG.warning("please use 'marker service start' first.")
            return 1
        LOG.info("cx_send: {0}".format(task_dict))
        sock.sendall(json.dumps(task_dict))


class MyTCPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global ACTIVE_TASK
        step = CONF.step
        logging.setup("marker")
        self.data = self.request.recv(1024).strip()
        task_dict = json.loads(self.data)
        LOG.info("cx_receive: {0}".format(task_dict))
        if task_dict.get("marker") == "exit":
            for k in ACTIVE_TASK:
                _stop_process(k)
            os._exit(os.EX_OK)
        inter_target = [x for x in ACTIVE_TASK if x in task_dict]
        for k in ACTIVE_TASK:
            if k not in inter_target:
                _stop_process(k)
        for k, v in task_dict.iteritems():
            if k not in inter_target:
                _start_process(k, step)
                for k1 in v:
                    if v[k1] == "running":
                        _handle_thread("add", k, k1)
        for item in inter_target:
            current_task = ACTIVE_TASK[item]
            dest_task = task_dict[item]
            inter_task = [x for x in current_task if x in dest_task]
            for task in current_task:
                if task not in inter_task:
                    _handle_thread("del", item, task)
            for task in dest_task:
                if task not in inter_task:
                    _handle_thread("add", item, task)
        ACTIVE_TASK = task_dict


def _start_process(target, step):
    LOG.info("start new process for {0}".format(target))
    global QUEUE_DICT
    q = Queue()
    p = Process(target=_run_process, args=(q, target, step))
    p.start()
    QUEUE_DICT[target] = (p, q)


def _stop_process(target):
    LOG.info("stop process for {0}".format(target))
    global QUEUE_DICT
    parent_conn = QUEUE_DICT[target][1]
    process = QUEUE_DICT[target][0]
    data = {"exit": "1"}
    parent_conn.put(json.dumps(data))
    process.join(WAIT_TIMEOUT)
    QUEUE_DICT.pop(target)


def _handle_thread(command, target, task):
    global QUEUE_DICT
    parent_conn = QUEUE_DICT[target][1]
    data = {command: task}
    parent_conn.put(json.dumps(data))


def _run_process(q, target, step):
    global TARGET_TASK
    while True:
        time.sleep(1)
        try:
            data = q.get(timeout=0.3)
            data = json.loads(data)
        except Empty:
            continue
        if data.get("exit"):
            try:
                q.get(timeout=0.3)
            except Empty:
                pass
            finally:
                q.close()
            os._exit(os.EX_OK)
        elif data.get("add"):
            task = data.get("add")
            LOG.info("start new thread for job {0} of {1}".format(
                task, target))
            TARGET_TASK.append(task)
            t = Thread(target=_run_thread, args=(target, task, step))
            t.start()
        elif data.get("del"):
            LOG.info("stop thread for job {0} of {1}".format(task, target))
            TARGET_TASK.remove(data.get("delete_task"))


def _run_thread(target, task, step):
    runner_cls = BaseProbes.get(task)
    runner_obj = runner_cls(target)
    runner_obj.check_db(step)
    while True:
        if task not in TARGET_TASK:
            return
        runner_obj.run()
        runner_obj.upload_data()
        time.sleep(step)
