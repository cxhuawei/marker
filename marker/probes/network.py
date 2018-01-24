import subprocess

from marker.probes import base_probes


@base_probes.configure("ping")
class Network(base_probes.BaseProbes):

    def __init__(self, target):
        super(Network, self).__init__(target)
        self.package_loss = None
        self.rrt = None

    def run(self):
        command = "ping {0} -c 100 -i 0.2 -w 1".format(self.target)
        result = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)
        if not result.returncode:
            result = result.stdout.readlines()
            self.package_loss = result[-2].split(",")[2].split("%")[0].strip()
            if result[-1] != "\n":
                self.rrt = result[-1].split("/")[4]
            self.data = {"package_loss": self.package_loss, "rrt": self.rrt}
        else:
            err = result.stderr.readlines()
            print(err)
