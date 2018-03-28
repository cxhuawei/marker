import os
import rrdtool

from marker.common import logging
from oslo_config import cfg


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _get_dir():
    data_dir = CONF.get("data_dir")
    if not data_dir.endswith("/"):
        data_dir = data_dir + "/"
    return data_dir


def db_create(target, item, step, ds, rra):
    ret = rrdtool.create("{0}{1}_{2}.rrd".format(_get_dir(), target, item),
                         "--step", str(step), "--start", "0", rra, ds)
    if ret:
        LOG.error(rrdtool.error())


def db_update(name, data):
    ret = rrdtool.update("{0}{1}.rrd".format(_get_dir(), name),
                         "N:{0}".format(data))
    if ret:
        LOG.error(rrdtool.error())


def db_check(target, job):
    db_name = "{0}{1}_{2}.rrd".format(_get_dir(), target, job)
    return os.path.isfile(db_name)
