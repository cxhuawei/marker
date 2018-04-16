import subprocess

from marker.common import db
from marker.probes import base_probes
from marker.common import logging
from subprocess import Popen


LOG = logging.getLogger(__name__)
ITEMS = {"bandwidth": {"DS": "DS:bw:GAUGE:60:0:U",
                       "RRA": "RRA:AVERAGE:0.5:12:1200"},
         "rrt": {"DS": "DS:rrt:GAUGE:60:0:U",
                 "RRA": "RRA:AVERAGE:0.5:12:1200"},
         "send_pps": {"DS": "DS:pps:GAUGE:60:0:U",
                      "RRA": "RRA:AVERAGE:0.5:12:1200"},
         "recv_pps": {"DS": "DS:pps:GAUGE:60:0:U",
                      "RRA": "RRA:AVERAGE:0.5:12:1200"}
         }


@base_probes.configure("network")
class Network(base_probes.BaseProbes):

    def __init__(self, server_ip, client_ip):
        super(Network, self).__init__(server_ip, client_ip)
        self.bw = None
        self.rrt = None
        self.send_pps = None
        self.recv_pps = None

    @classmethod
    def check_db(self, step, ip):
        for item, value in ITEMS.iteritems():
            if not db.db_check(ip, item):
                db.db_create(ip, item, step,
                             value["DS"], value["RRA"])

    def run(self, addition={}):
        if addition.get("qperf_port"):
            port = addition.get("qperf_port")
        else:
            LOG.error("qperf port must be configed.")
            return 1
        command = "qperf {0} -lp {1} tcp_bw tcp_lat".format(self.server_ip,
                                                            port)
        result = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)
        result.wait()
        if not result.returncode:
            result = result.stdout.readlines()
            if len(result) == 4:
                try:
                    bw_value = float(
                        result[1].split("=")[1].strip().split(" ")[0])
                    bw_unit = result[1].split("=")[1].strip().split(" ")[1]
                    if bw_unit[0] == "M":
                        pass
                    elif bw_unit[0] == "K":
                        bw_value = bw_value/1000
                    elif bw_unit[0] == "G":
                        bw_value = bw_value*1000
                    elif bw_unit[0] == "B":
                        bw_value = bw_value/1000000
                    self.bw = bw_value

                    rrt_value = float(
                        result[3].split("=")[1].strip().split(" ")[0])
                    rrt_unit = result[3].split("=")[1].strip().split(" ")[1]
                    if rrt_unit[0] == "m":
                        rrt_value = rrt_value/1000
                    elif rrt_unit[0] == "s":
                        pass
                    elif rrt_unit[0] == "u":
                        rrt_value = rrt_value/1000000
                    self.rrt = rrt_value
                except Exception as e:
                    LOG.error(e)
                    self.bw = None
                    self.rrt = None
            else:
                self.bw = None
                self.rrt = None
        else:
            self.bw = None
            self.rrt = None
            err = result.stderr.readlines()
            LOG.error(err)
        command = "qperf {0} -m 1 -lp {1} udp_bw".format(self.server_ip, port)
        result = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)
        result.wait()
        if not result.returncode:
            result = result.stdout.readlines()
            if len(result) == 3:
                try:
                    send_value = float(
                        result[1].split("=")[1].strip().split(" ")[0])
                    send_unit = result[1].split("=")[1].strip().split(" ")[1]
                    if send_unit[0] == "K":
                        pass
                    elif send_unit[0] == "M":
                        send_value = send_value*1000
                    elif send_unit[0] == "G":
                        send_value = send_value*1000000
                    elif send_unit[0] == "B":
                        send_value = send_value/1000
                    self.send_pps = send_value

                    recv_value = float(
                        result[2].split("=")[1].strip().split(" ")[0])
                    recv_unit = result[2].split("=")[1].strip().split(" ")[1]
                    if recv_unit[0] == "K":
                        pass
                    elif recv_unit[0] == "M":
                        recv_value = recv_value*1000
                    elif recv_unit[0] == "G":
                        recv_value = recv_value*1000000
                    elif recv_unit[0] == "B":
                        recv_value = recv_value/1000
                    self.recv_pps = recv_value
                except Exception as e:
                    LOG.error(e)
                    self.send_pps = None
                    self.recv_pps = None
            else:
                self.send_pps = None
                self.recv_pps = None
        else:
            self.send_pps = None
            self.recv_pps = None
            err = result.stderr.readlines()
            LOG.error(err)
        self.data = {"bandwidth": self.bw, "rrt": self.rrt,
                     "send_pps": self.send_pps, "recv_pps": self.recv_pps}
        return result

    def run_as_server(self, addition={}):
        if addition.get("qperf_port"):
            port = addition.get("qperf_port")
        else:
            LOG.error("qperf port must be configed.")
            return 1
        command = "qperf -lp {0}".format(port)
        t = Popen(command, shell=True)
        return t
