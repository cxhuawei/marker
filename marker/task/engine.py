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
ACTIVE_TASK = []
QUEUE_DICT = {}

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class TaskEngine(object):

    @classmethod
    def run(cls, action, task_list, server_ip, target):
        global ACTIVE_TASK
        if action == "start":
            if not task_list:
                task_list = cls._get_local_task()
            for task in task_list:
                if task not in ACTIVE_TASK:
                    _start_process(task, server_ip, target)
                    ACTIVE_TASK.append(task)
        elif action == "stop":
            if not task_list:
                task_list = cls._get_local_task()
            for task in task_list:
                if task in ACTIVE_TASK:
                    _stop_process(task, server_ip, target)
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


def _start_process(task_name, server_ip, target):
    LOG.info("start new process for {0}".format(task_name))
    step = CONF.get("{0}_step".format(task_name))
    global QUEUE_DICT
    q = Queue()
    p = Process(target=_run_process, args=(q, task_name, server_ip,
                                           target, step))
    p.start()
    QUEUE_DICT[task_name] = (p, q)
    utils.send(
        "comfirm", server_ip,
        data={"type": "start", "task": task_name, "step": step})


def _stop_process(task_name, server_ip, target):
    LOG.info("stop process for {0}".format(task_name))
    global QUEUE_DICT
    parent_conn = QUEUE_DICT[task_name][1]
    process = QUEUE_DICT[task_name][0]
    data = {"exit": "1"}
    parent_conn.put(json.dumps(data))
    process.join(WAIT_TIMEOUT)
    QUEUE_DICT.pop(task_name)
    utils.send(
        "comfirm", server_ip,
        data={"type": "stop", "task": task_name})


def _run_process(q, task_name, server_ip, target, step):
    runner_cls = BaseProbes.get(task_name)
    runner_obj = runner_cls(target)
    while True:
        runner_obj.run()
        runner_obj.upload_data(server_ip)
        time.sleep(step)
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
