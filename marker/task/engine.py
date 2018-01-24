import json
import os
import SocketServer
import socket
import time

from marker.probes.base_probes import BaseProbes
from marker.task import daemon
from multiprocessing import Process
from multiprocessing import Queue
from Queue import Empty
from threading import Thread

HOST = "localhost"
PORT = 9999
WAIT_TIMEOUT = 5
ACTIVE_TASK = {}
TARGET_TASK = []
QUEUE_DICT = {}


class TaskEngine(object):

    @classmethod
    def run(cls, task_dict):
        cls._update_task(task_dict)

    @classmethod
    def _create_server(cls):
        #with daemon.DaemonContext():
        server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)
        server.serve_forever()

    @classmethod
    def _update_task(cls, task_dict):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
        except Exception as e:
            print(e)
            cls._create_server()
            sock.connect((HOST, PORT))
        sock.sendall(json.dumps(task_dict))
        sock.close()


class MyTCPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global ACTIVE_TASK
        self.data = self.request.recv(1024).strip()
        task_dict = json.loads(self.data)
        inter_target = [x for x in ACTIVE_TASK if x in task_dict]
        for k in ACTIVE_TASK:
            if k not in inter_target:
                _stop_process(k)
        for k, v in task_dict.iteritems():
            if k not in inter_target:
                _start_process(k)
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


def _start_process(target):
    print("start new process for {0}".format(target))
    global QUEUE_DICT
    q = Queue()
    p = Process(target=_run_process, args=(q, target))
    p.start()
    QUEUE_DICT[target] = (p, q)


def _stop_process(target):
    print("stop process for {0}".format(target))
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


def _run_process(q, target):
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
            print("start new thread for job {0} of {1}".format(task, target))
            TARGET_TASK.append(task)
            t = Thread(target=_run_thread, args=(target, task))
            t.start()
            # t.join()
        elif data.get("del"):
            print("stop thread for job {0} of {1}".format(task, target))
            TARGET_TASK.remove(data.get("delete_task"))


def _run_thread(target, task):
    while True:
        if task not in TARGET_TASK:
            return
        runner_cls = BaseProbes.get(task)
        runner_obj = runner_cls(target)
        runner_obj.run()
        time.sleep(5)
