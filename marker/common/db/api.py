import rrdtool


def db_create(name, item, dstype, timeout, min, max, step=300):
    ret = rrdtool.create("{0}.rrd".format(name),
                         "--step", step, "--start", "0",
                         "DS:{0}:{1}:{2}:{3}:{4}".format(
                             item, dstype, timeout, min, max))
    if ret:
        print(rrdtool.error())


def db_update(name, data):
    ret = rrdtool.update("{0.rrd}".format(name), "N:{0}".format(data))
    if ret:
        print(rrdtool.error())


def db_check(name):
    pass
