import os
import sys

from oslo_config import cfg
from marker.common import logging
from marker.common import objects
from marker.task import engine
from requests.packages import urllib3


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class APIGroup(object):
    def __init__(self, api):
        """Initialize API group

        """

        self.api = api

    def _generate_task_dict(self, command, target=None, task=None):
        task_dict = objects.Task().list()
        if target and task:
            for k, v in task_dict:
                if k != target:
                    active_tag = False
                    for k1, v1 in v:
                        if v1 == "running":
                            active_tag = True
                            break
                    if not active_tag:
                        task_dict.pop(k)
                else:
                    active_tag = False
                    for k1, v1 in v:
                        if k1 == task:
                            v1 = command
                        if v1 == "running":
                            active_tag = True
                    if not active_tag:
                        task_dict.pop(k)
        elif target:
            for k, v in task_dict:
                if k != target:
                    active_tag = False
                    for k1, v1 in v:
                        if v1 == "running":
                            active_tag = True
                            break
                    if not active_tag:
                        task_dict.pop(k)
                else:
                    task_dict[k] = {x: command for x, y in v.iteritems()}
                    if command == "stop":
                        task_dict.pop(k)
        elif task:
            for k, v in task_dict:
                active_tag = False
                for k1, v1 in v:
                    if k1 == task:
                        v1 = command
                    if v1 == "running":
                        active_tag = True
                if not active_tag:
                    task_dict.pop(k)

        else:
            for k, v in task_dict:
                task_dict[k] = {x: command for x, y in v.iteritems()}
                if command == "stop":
                    task_dict.pop(k)
        return task_dict


class _Target(APIGroup):

    def add(self, target):
        objects.Target().add(target)

    def delete(self, target):
        objects.Target().delete(target)

    def start(self, target):
        task_dict = self._generate_task_dict("running", target=target)
        engine.TaskEngine.run(task_dict)

    def stop(self, target):
        task_dict = self._generate_task_dict("stop", target=target)
        engine.TaskEngine.run(task_dict)

    def list(self, task):
        objects.Target().list(task)


class _Task(APIGroup):

    def add(self, task, target):
        objects.Task().add(task, target)

    def delete(self, task, target):
        objects.Task().add(task, target)

    def start(self, task, target):
        task_dict = self._generate_task_dict("start", target=target, task=task)
        engine.TaskEngine.run(task_dict)

    def stop(self, task, target):
        task_dict = self._generate_task_dict("stop", target=target, task=task)
        engine.TaskEngine.run(task_dict)

    def list(self, target):
        objects.Task().list(target)


class API(object):

    CONFIG_SEARCH_PATHS = [sys.prefix + "/etc/marker",
                           "~/.marker", "/etc/marker"]
    CONFIG_FILE_NAME = "marker.conf"

    def __init__(self, config_file=None, config_args=None,
                 plugin_paths=None, skip_db_check=False):
        """Initialize Marker API instance

        :param config_file: Path to marker configuration file. If None, default
                            path will be selected
        :type config_file: str
        :param config_args: Arguments for initialization current configuration
        :type config_args: list
        :param plugin_paths: Additional custom plugin locations
        :type plugin_paths: list
        :param skip_db_check: Allows to skip db revision check
        :type skip_db_check: bool
        """

        try:
            config_files = ([config_file] if config_file else
                            self._default_config_file())
            CONF(config_args or [],
                 project="marker",
                 version="1.0",
                 default_config_files=config_files)

            logging.setup("marker")
            if not CONF.get("log_config_append"):
                LOG.debug(
                    "INFO logs from urllib3 and requests module are hide.")
                requests_log = logging.getLogger("requests").logger
                requests_log.setLevel(logging.WARNING)
                urllib3_log = logging.getLogger("urllib3").logger
                urllib3_log.setLevel(logging.WARNING)

                LOG.debug("urllib3 insecure warnings are hidden.")
                for warning in ("InsecurePlatformWarning",
                                "SNIMissingWarning",
                                "InsecureRequestWarning"):
                    warning_cls = getattr(urllib3.exceptions, warning, None)
                    if warning_cls is not None:
                        urllib3.disable_warnings(warning_cls)

            # NOTE(wtakase): This is for suppressing boto error logging.
            LOG.debug("ERROR log from boto module is hide.")
            boto_log = logging.getLogger("boto").logger
            boto_log.setLevel(logging.CRITICAL)

            # Set alembic log level to ERROR
            alembic_log = logging.getLogger("alembic").logger
            alembic_log.setLevel(logging.ERROR)

        except cfg.ConfigFilesNotFoundError as e:
            cfg_files = e.config_files
            raise Exception(
                "Failed to read configuration file(s): %s" % cfg_files)

        self._target = _Target(self)
        self._task = _Task(self)

    def _default_config_file(self):
        for path in self.CONFIG_SEARCH_PATHS:
            abspath = os.path.abspath(os.path.expanduser(path))
            fpath = os.path.join(abspath, self.CONFIG_FILE_NAME)
            if os.path.isfile(fpath):
                return [fpath]

    @property
    def target(self):
        return self._target

    @property
    def task(self):
        return self._task

    @property
    def version(self):
        return 1
