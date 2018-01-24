from marker.probes import base_probes


@base_probes.configure("demo")
class Demo(base_probes.BaseProbes):

    def __init__(self, target):
        super(Demo, self).__init__(target)

    def run(self):
        print self.target
