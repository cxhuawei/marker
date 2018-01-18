import json
import SocketServer
import socket
import time

from marker.task import daemon
from multiprocessing import Process
from multiprocessing import Pipe
from threading import Thread

HOST = "localhost"
PORT = 9999
ACTIVE_TASK = {}
TARGET_TASK = []
PIPE_DICT = {}


class TaskEngine(object):

    def run(self, task_dict):
        self._update_task(task_dict)

    def _create_server(self):
        with daemon.DaemonContext():
            server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)
            server.serve_forever()

    def _update_task(self, task_dict):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(HOST, PORT)
            sock.sendall(json.dumps(task_dict))
            sock.close()
        except Exception as e:
            print(e)
            self._create_server()


class MyTCPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global ACTIVE_TASK

        self.data = self.request.recv(1024).strip()
        task_dict = json.loads(self.data)
        inter_target = [x for x in ACTIVE_TASK if x in task_dict]
        for k in ACTIVE_TASK:
            if k not in inter_target:
                _stop_process(k)
        for k, v in task_dict:
            if k not in inter_target:
                _start_process(k)
                for k1 in v:
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
    global PIPE_DICT
    parent_conn, child_conn = Pipe()
    p = Process(target=_run_process, args=(child_conn, target))
    p.start()
    p.join()
    PIPE_DICT[target] = parent_conn


def _stop_process(target):
    global PIPE_DICT
    parent_conn = PIPE_DICT[target]
    data = {"exit": True}
    parent_conn.send(data)
    parent_conn.close()
    PIPE_DICT.pop(target)


def _handle_thread(command, target, task):
    global PIPE_DICT
    parent_conn = PIPE_DICT[target]
    data = {command: task}
    parent_conn.send(data)


def _run_process(conn, target):
    global TARGET_TASK
    while True:
        data = conn.recv()
        data = json.loads(data)
        if data.get("exit"):
            conn.close()
            Process.terminate()
        elif data.get("add"):
            task = data.get("add")
            t = Thread(target=_run_thread, args=(target, task))
            t.start()
            t.join()
            TARGET_TASK.append(task)
        elif data.get("del"):
            TARGET_TASK.remove(data.get("delete_task"))
        time.sleep(1)


def _run_thread(target, task):
    while True:
        if task not in TARGET_TASK:
            return
        #TODO by chenxu
        #get probes and run it
        time.sleep(1)
