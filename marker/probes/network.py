import subprocess

from marker.common import db
from marker.probes import base_probes
from marker.common import logging


LOG = logging.getLogger(__name__)
ITEMS = {"package_loss": {"DS": "DS:loss:GAUGE:60:0:100",
                          "RRA": "RRA:MAX:0.5:4:200"},
         "rrt": {"DS": "DS:rrt:GAUGE:60:0:U",
                 "RRA": "RRA:AVERAGE:0.5:4:200"}
         }
RUN_TIME = 20


@base_probes.configure("ping")
class Network(base_probes.BaseProbes):

    def __init__(self, target):
        super(Network, self).__init__(target)
        self.package_loss = None
        self.rrt = None

    def check_db(self, step):
        for item, value in ITEMS.iteritems():
            if not db.db_check(self.target, item):
                db.db_create(self.target, item, step + RUN_TIME,
                             value["DS"], value["RRA"])

    def run(self):
        command = "ping {0} -c 100 -i 0.2 -w 100".format(self.target)
        result = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)
        if not result.returncode:
            result = result.stdout.readlines()
            self.package_loss = result[-2].split(",")[2].split("%")[0].strip()
            if result[-1] != "\n":
                self.rrt = result[-1].split("/")[4]
            else:
                self.rrt = None
        else:
            self.package_loss = None
            self.rrt = None
            err = result.stderr.readlines()
            LOG.error(err)
        self.data = {"package_loss": self.package_loss, "rrt": self.rrt}
