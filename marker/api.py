import copy
import os
import sys

from oslo_config import cfg
from marker.common import logging
from marker.common import objects
from marker.probes.base_probes import BaseProbes
from marker.server.tcp_server import ServiceEngine
from marker.server import utils
from requests.packages import urllib3


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class APIGroup(object):

    def __init__(self, api):
        """Initialize API group

        """

        self.api = api

    def _update_task_obj(self, action, targets=None, task=None):
        task_obj = objects.Task()
        task_dict = task_obj.list()
        if not targets:
            targets = [k for k in task_dict]
        for target in targets:
            if task:
                task_dict[target][task] = action
            else:
                for k in task_dict[target]:
                    task_dict[target][k] = action
        task_obj.update(task_dict)

    def _send_command(self, action, targets=None, task=None):
        task_obj = objects.Task()
        task_dict = task_obj.list()
        if not targets and not task:
            targets = {}
            for k, v in task_dict.iteritems():
                targets[k] = [k1 for k1 in v]
        elif not targets and task:
            targets = {k: [task] for k,
                       v in task_dict.iteritems() if task in v}
        elif targets and not task:
            targets = {targets: [k for k in task_dict[targets]]}
        else:
            targets = {targets: [task]}
        for target, task in targets.iteritems():
            utils.send(action, target, data=task)


class _Target(APIGroup):

    def add(self, targets):
        targets_dict = copy.deepcopy(targets)
        for target in targets_dict:
            if utils.send("connect", target):
                LOG.error("Add {0} failed.".format(target))
                targets.remove(target)
        objects.Target().add(targets)

    def delete(self, targets):
        objects.Target().delete(targets)

    def start(self, targets):
        self._send_command("start", targets=targets)
        self._update_task_obj("start", targets=targets)

    def stop(self, targets):
        self._send_command("stop", targets=targets)
        self._update_task_obj("stop", targets=targets)

    @classmethod
    def list(self, task=None):
        targets = objects.Target().list(task)
        print(targets)


class _Task(APIGroup):

    def add(self, task, target):
        if target:
            if utils.send("connect", target):
                LOG.error("Add {0} to {1} failed.".format(task, target))
                return
        else:
            target = objects.Target().list()
            target_dict = copy.deepcopy(target)
            for target in target_dict:
                if utils.send("connect", target):
                    LOG.error("Add {0} to {1} failed.".format(task, target))
                    target.remove(target)
        if target:
            objects.Task().add(task, target)

    def delete(self, task, target):
        objects.Task().delete(task, target)

    def start(self, task, targets=None):
        self._send_command("start", task=task, targets=targets)
        self._update_task_obj("start", task=task, targets=targets)

    def stop(self, task, targets=None):
        self._send_command("stop", task=task, targets=targets)
        self._update_task_obj("stop", task=task, targets=targets)

    @classmethod
    def list(self, target=None):
        tasks = []
        if target:
            tasks = objects.Task().list(target)
        else:
            for p in BaseProbes.get_all():
                tasks.append(p.get_name())
        print(tasks)


class _Service(APIGroup):

    def start(self):
        ServiceEngine.start()

    def stop(self):
        targets = objects.Target().list()
        ServiceEngine.stop(targets)


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
            from marker.probes.network import Network
            tasks = []
            for p in BaseProbes.get_all():
                tasks.append(p.get_name())
            for task in tasks:
                OPTS = [cfg.IntOpt(
                    "{0}_step".format(task),
                    default=5,
                    help="specifies the base interval in seconds"
                         " with which data will fed into the rrd."
                )]
                CONF.register_opts(OPTS)
            HOST_OPTS = [cfg.StrOpt(
                "host",
                default="localhost",
                help="specifies host of marker service.")]
            PORT_OPTS = [cfg.IntOpt(
                "port",
                default=9999,
                help="specifies port of marker service.")]
            DATA_OPTS = [cfg.StrOpt(
                "data_dir",
                default="/opt/marker/",
                help="dir where paste rrd files and marker.json.")]
            CONF.register_opts(HOST_OPTS)
            CONF.register_opts(PORT_OPTS)
            CONF.register_opts(DATA_OPTS)
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
        self._service = _Service(self)

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
    def service(self):
        return self._service

    @property
    def version(self):
        return 1
