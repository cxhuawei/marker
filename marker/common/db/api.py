import os
import rrdtool

from marker.common import logging


LOG = logging.getLogger(__name__)


def db_create(target, item, step, ds, rra):
    ret = rrdtool.create("{0}_{1}.rrd".format(target, item),
                         "--step", str(step), "--start", "0", rra, ds)
    if ret:
        LOG.error(rrdtool.error())


def db_update(name, data):
    ret = rrdtool.update("{0}.rrd".format(name), "N:{0}".format(data))
    if ret:
        LOG.error(rrdtool.error())


def db_check(target, job):
    db_name = "{0}_{1}.rrd".format(target, job)
    return os.path.isfile(db_name)
