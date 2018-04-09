import os
import subprocess

from marker.common import db
from marker.probes import base_probes
from marker.common import logging
from threading import Thread


LOG = logging.getLogger(__name__)
ITEMS = {"bw": {"DS": "DS:bw:GAUGE:60:0:U",
                "RRA": "RRA:AVERAGE:0.5:12:1200"},
         "rrt": {"DS": "DS:rrt:GAUGE:60:0:U",
                 "RRA": "RRA:AVERAGE:0.5:12:1200"},
         "pps": {"DS": "DS:pps:GAUGE:60:0:U",
                 "RRA": "RRA:AVERAGE:0.5:12:1200"}
         }


@base_probes.configure("network")
class Network(base_probes.BaseProbes):

    def __init__(self, target):
        super(Network, self).__init__(target)
        self.bw = None
        self.rrt = None
        self.send_pps = None
        self.recv_pps = None

    def check_db(self, step):
        for item, value in ITEMS.iteritems():
            if not db.db_check(self.target, item):
                db.db_create(self.target, item, step,
                             value["DS"], value["RRA"])

    def run(self, addition=None):
        if not addition and hasattr(addition, "get") and addition.get("qperf"):
            port = addition.get("qperf")
        else:
            return 1
        command = "qperf {0} -lp {1} tcp_bw tcp_lat".format(self.target, port)
        result = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)
        if not result.returncode:
            result = result.stdout.readlines()
            if len(result) == 4:
                bw_value = result[1].split("=")[1].split("")[0]
                bw_unit = result[1].split("=")[1].split("")[1]
                if bw_unit[0] == "M":
                    pass
                elif bw_unit[0] == "K":
                    bw_value = float(bw_value)/1000
                elif bw_unit[0] == "G":
                    bw_value = bw_value*1000
                elif bw_unit[0] == "B":
                    bw_value = float(bw_value)/1000000
                self.bw = bw_value

                rrt_value = result[3].split("=")[1].split("")[0]
                rrt_unit = result[3].split("=")[1].split("")[1]
                if rrt_unit[0] == "m":
                    rrt_value = float(rrt_value)/1000
                elif rrt_unit[0] == "s":
                    pass
                elif rrt_unit[0] == "u":
                    rrt_value = float(rrt_value)/1000000
                self.rrt = rrt_value
            else:
                self.bw = None
                self.rrt = None
        else:
            self.bw = None
            self.rrt = None
            err = result.stderr.readlines()
            LOG.error(err)
        command = "qperf {0} -m 1 -lp {1} udp_bw".format(self.target, port)
        result = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)
        if not result.returncode:
            result = result.stdout.readlines()
            if len(result) == 3:
                send_value = result[1].split("=")[1].split("")[0]
                send_unit = result[1].split("=")[1].split("")[1]
                if send_unit[0] == "K":
                    pass
                elif send_unit[0] == "M":
                    send_value = send_value*1000
                elif send_unit[0] == "G":
                    send_value = send_value*1000000
                elif send_unit[0] == "B":
                    send_value = float(send_value)/1000
                self.send_pps = send_value

                recv_value = result[2].split("=")[1].split("")[0]
                recv_unit = result[2].split("=")[1].split("")[1]
                if recv_unit[0] == "K":
                    pass
                elif recv_unit[0] == "M":
                    recv_value = recv_value*1000
                elif recv_unit[0] == "G":
                    recv_value = recv_value*1000000
                elif recv_unit[0] == "B":
                    recv_value = float(recv_value)/1000
                self.recv_pps = recv_value
            else:
                self.send_pps = None
                self.recv_pps = None
        else:
            self.send_pps = None
            self.recv_pps = None
            err = result.stderr.readlines()
            LOG.error(err)
            self.data = {"bandwidth": self.wd, "rrt": self.rrt,
                         "send_pps": self.send_pps, "recv_pps": self.recv_pps}

    def run_as_server(self, addition):
        if not addition and hasattr(addition, "get") and addition.get("qperf"):
            port = addition.get("qperf")
        else:
            return 1
        command = "qperf -lp {0}".format(port)
        try:
            t = Thread(target=os.system(command))
            t.start()
        except Exception as e:
            LOG.error(e)
            return 1
