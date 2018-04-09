import json
import os
import time

from marker.common import logging
from marker.common.objects import targetandtask
from marker.probes.base_probes import BaseProbes
from marker.server import utils
from multiprocessing import Process
from multiprocessing import Queue
from oslo_config import cfg
from Queue import Empty

WAIT_TIMEOUT = 5
ACTIVE_TASK_CLIENT = []
ACTIVE_TASK_SERVER = []
QUEUE_DICT = {}

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class TaskEngine(object):

    @classmethod
    def run(cls, action, task_list, server_ip, target, role, addition):
        global ACTIVE_TASK_CLIENT
        global ACTIVE_TASK_SERVER
        if role == "client":
            ACTIVE_TASK = ACTIVE_TASK_CLIENT
        else:
            ACTIVE_TASK = ACTIVE_TASK_SERVER
        if action == "start":
            if not task_list:
                task_list = cls._get_local_task()
            for task in task_list:
                if task not in ACTIVE_TASK:
                    _start_process(task, server_ip, target, role, addition)
                    ACTIVE_TASK.append(task)
        elif action == "stop":
            if not task_list:
                task_list = cls._get_local_task()
            for task in task_list:
                if task in ACTIVE_TASK:
                    _stop_process(task, server_ip, target, role)
                    ACTIVE_TASK.remove(task)

    def _get_local_task(cls):
        task_list = []
        for p in BaseProbes.get_all():
            task_list.append(p.get_name())

    @classmethod
    def check_db(cls, target, task_name, step):
        runner_cls = BaseProbes.get(task_name)
        runner_obj = runner_cls(target)
        runner_obj.check_db(step)

    @classmethod
    def upload_data(cls, target, data):
        targetandtask.upload_data(target, data)


def _start_process(task_name, server_ip, target, role, addition):
    LOG.info("start new process for {0} as {1}".format(task_name, role))
    step = getattr(CONF, task_name).get("step", 5)
    global QUEUE_DICT
    q = Queue()
    p = Process(target=_run_process, args=(q, task_name, server_ip,
                                           target, step, role, addition))
    p.start()
    QUEUE_DICT["{0}_{1}".format(task_name, role)] = (p, q)
    utils.send(
        "comfirm", server_ip,
        data={"type": "start", "task": task_name, "step": step})


def _stop_process(task_name, server_ip, target, role):
    LOG.info("stop process for {0} as {1}".format(task_name, role))
    global QUEUE_DICT
    parent_conn = QUEUE_DICT["{0}_{1}".format(task_name, role)][1]
    process = QUEUE_DICT["{0}_{1}".format(task_name, role)][0]
    data = {"exit": "1"}
    parent_conn.put(json.dumps(data))
    process.join(WAIT_TIMEOUT)
    QUEUE_DICT.pop("{0}_{1}".format(task_name, role))
    utils.send(
        "comfirm", server_ip,
        data={"type": "stop", "task": task_name})


def _run_process(q, task_name, server_ip, target, step, role, addition):
    runner_cls = BaseProbes.get(task_name)
    runner_obj = runner_cls(target)
    if role == "client":
        utils.send("comfirm", server_ip,
                   data={"type": "start",
                         "task": task_name,
                         "step": step,
                         "role": "client",
                         "status": "success"})
        while True:
            runner_obj.run(addition)
            runner_obj.upload_data(server_ip)
            time.sleep(step)
            _wait_quit(q)
    else:
        client_ip = addition.get("client_ip")
        if runner_obj.run_as_server(addition):
            utils.send("comfirm", server_ip,
                       data={"type": "start",
                             "task": task_name,
                             "role": "server",
                             "status": "failed",
                             "client_ip": client_ip})
            os._exit(os.EX_OK)
        utils.send("comfirm", server_ip,
                   data={"type": "start",
                         "task": task_name,
                         "role": "server",
                         "status": "success",
                         "client_ip": client_ip})
        while True:
            _wait_quit(q)


def _wait_quit(q):
    try:
        data = q.get(timeout=0.3)
        data = json.loads(data)
    except Empty:
        pass
    if data.get("exit"):
        try:
            q.get(timeout=0.3)
        except Empty:
            pass
        finally:
            q.close()
        os._exit(os.EX_OK)
