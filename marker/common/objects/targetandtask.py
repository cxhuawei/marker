import json
import os
import sys

from marker.common import logging
from marker.common import db

LOG = logging.getLogger(__name__)
CONFIG_SEARCH_PATHS = [sys.prefix + "/etc/marker", "~/.marker", "/etc/marker"]
CONFIG_FILE_NAME = "marker.json"


def _default_context_file():
    for path in CONFIG_SEARCH_PATHS:
        abspath = os.path.abspath(os.path.expanduser(path))
        fpath = os.path.join(abspath, CONFIG_FILE_NAME)
        if os.path.isfile(fpath):
            return fpath


def _read_context():
    path = _default_context_file()
    with open(path, "r") as f:
        return json.load(f)


def _write_context(context):
    path = _default_context_file()
    with open(path, "w") as f:
        json.dump("context", f)


def upload_data(target, data):
    for k, v in data:
        if db.db_check(target, k):
            db.db_update("{0}_{1}".format(target, k), v)
        else:
            db.db_create(target, k)


class Target(object):

    def __init__(self):
        self.context = _read_context()

    def add(self, target):
        if target in self.context:
            LOG.debug("{0} already in Target.".format(target))
        else:
            self.context[target] = {}
            _write_context(self.context)
            LOG.info("add {0} success.".format(target))

    def delete(self, target):
        if target in self.context:
            self.context.pop(target)
            _write_context(self.context)
            LOG.info("delete {0} success.".format(target))
        else:
            LOG.debug("{0} not in Target.".format(target))

    def list(self, task):
        target = []
        for k, v in self.context:
            if not task or {x: y for x, y in v.iteritems() if x == task}:
                target.push(k)
        return target


class Task(object):

    def __init__(self):
        self.context = _read_context()

    def add(self, task, target):
        if not target:
            for k, v in self.context:
                if task not in v:
                    v[task] = "stop"
                    LOG.info("add Task {0} to Target {1} success.".format(
                        task, target))
        elif target in self.context:
            if task in self.context[target]:
                LOG.debug(
                    "Task {0} already in Target {1}.".format(task, target))
            else:
                self.context[target][task] = "stop"
                LOG.info(
                    "add Task {0} to Target {1} success.".format(task, target))
        else:
            LOG.debug("{0} not in Target.".format(target))
        _write_context(self.context)

    def delete(self, task, target):
        if not target:
            for k, v in self.context:
                if task in v:
                    v.pop(task)
                    LOG.info("remove Task {0} from Target {1} success.".format(
                        task, target))
        elif target in self.context:
            if task in self.context[target]:
                self.context[target].pop(task)
                LOG.info("remove Task {0} from Target {1} success.".format(
                    task, target))
            else:
                LOG.debug("Task {0} not in Target {1}.".format(task, target))
        else:
            LOG.debug("{0} not in Target.".format(target))
        _write_context(self.context)

    def list(self, target):
        task = []
        if target:
            task = [x for x, y in self.context[target].iteritems()]
            return task
        else:
            return self.context
