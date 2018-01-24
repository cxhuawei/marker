# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function

import argparse
import inspect
import os
import sys
import warnings

from oslo_config import cfg
from oslo_utils import encodeutils
import six

from marker import api
from marker.common import logging


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


# Some CLI-specific constants
MARGIN = 3


class MissingArgs(Exception):
    """Supplied arguments are not sufficient for calling a function."""
    def __init__(self, missing):
        self.missing = missing
        msg = "Missing arguments: %s" % ", ".join(missing)
        super(MissingArgs, self).__init__(msg)


def validate_args(fn, *args, **kwargs):
    """Check that the supplied args are sufficient for calling a function.

    >>> validate_args(lambda a: None)
    Traceback (most recent call last):
        ...
    MissingArgs: Missing argument(s): a
    >>> validate_args(lambda a, b, c, d: None, 0, c=1)
    Traceback (most recent call last):
        ...
    MissingArgs: Missing argument(s): b, d

    :param fn: the function to check
    :param args: the positional arguments supplied
    :param kwargs: the keyword arguments supplied
    """
    argspec = inspect.getargspec(fn)

    num_defaults = len(argspec.defaults or [])
    required_args = argspec.args[:len(argspec.args) - num_defaults]

    if getattr(fn, "__self__", None):
        required_args.pop(0)

    missing_required_args = required_args[len(args):]
    missing = [arg for arg in missing_required_args if arg not in kwargs]
    if missing:
        raise MissingArgs(missing)


def suppress_warnings(f):
    f._suppress_warnings = True
    return f


class CategoryParser(argparse.ArgumentParser):

    """Customized arguments parser

    We need this one to override hardcoded behavior.
    So, we want to print item's help instead of 'error: too few arguments'.
    Also, we want not to print positional arguments in help message.
    """

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        # INFO(oanufriev) _action_groups[0] contains positional arguments.
        for action_group in self._action_groups[1:]:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def error(self, message):
        self.print_help(sys.stderr)
        if message.startswith("argument") and message.endswith("is required"):
            # NOTE(pirsriva) Argparse will currently raise an error
            # message for only 1 missing argument at a time i.e. in the
            # error message it WILL NOT LIST ALL the missing arguments
            # at once INSTEAD only 1 missing argument at a time
            missing_arg = message.split()[1]
            print("Missing argument:\n%s" % missing_arg)
        sys.exit(2)


def pretty_float_formatter(field, ndigits=None):
    """Create a float value formatter function for the given field.

    :param field: str name of an object, which value should be formatted
    :param ndigits: int number of digits after decimal point to round
                    default is None - this disables rounding
    :returns: field formatter function
    """
    def _formatter(obj):
        value = obj[field] if isinstance(obj, dict) else getattr(obj, field)
        if type(value) in (int, float):
            if ndigits:
                return round(value, ndigits)
            return value
        return "n/a"
    return _formatter


def args(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault("args", []).insert(0, (args, kwargs))
        if "metavar" not in kwargs and "action" not in kwargs:
            # NOTE(andreykurilin): argparse constructs awful metavars...
            kwargs["metavar"] = "<%s>" % args[0].replace(
                "--", "").replace("-", "_")
        return func
    return _decorator


def alias(command_name):
    """Allow cli to use alias command name instead of function name.

    :param command_name: desired command name
    """
    def decorator(func):
        func.alias = command_name
        return func
    return decorator


def deprecated_args(*args, **kwargs):
    def _decorator(func):
        if "release" not in kwargs:
            raise ValueError("'release' is required keyword argument of "
                             "'deprecated_args' decorator.")
        func.__dict__.setdefault("args", []).insert(0, (args, kwargs))
        func.__dict__.setdefault("deprecated_args", [])
        func.deprecated_args.append(args[0])

        help_msg = "[Deprecated since Marker %s] " % kwargs.pop("release")
        if "alternative" in kwargs:
            help_msg += "Use '%s' instead. " % kwargs.pop("alternative")
        if "help" in kwargs:
            help_msg += kwargs["help"]
        kwargs["help"] = help_msg
        return func
    return _decorator


def help_group(uuid):
    """Label cli method with specific group.

    Joining methods by groups allows to compose more user-friendly help
    messages in CLI.

    :param uuid: Name of group to find common methods. It will be used for
        sorting groups in help message, so you can start uuid with
        some number (i.e "1_launcher", "2_management") to put groups in proper
        order. Note: default group had "0" uuid.
    """

    def wrapper(func):
        func.help_group = uuid
        return func
    return wrapper


def _methods_of(cls):
    """Get all callable methods of a class that don't start with underscore.

    :returns: a list of tuples of the form (method_name, method)
    """
    # The idea of unbound methods exists in Python 2 and was removed in
    # Python 3, so "inspect.ismethod" is used here for Python 2 and
    # "inspect.isfunction" for Python 3.
    all_methods = inspect.getmembers(
        cls, predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x))
    methods = [m for m in all_methods if not m[0].startswith("_")]

    help_groups = {}
    for m in methods:
        group = getattr(m[1], "help_group", "0")
        help_groups.setdefault(group, []).append(m)

    if len(help_groups) > 1:
        # we should sort methods by groups
        methods = []
        for group in sorted(help_groups.items(), key=lambda x: x[0]):
            if methods:
                # None -> empty line between groups
                methods.append((None, None))
            methods.extend(group[1])
    return methods


def _add_command_parsers(categories, subparsers):

    # INFO(oanufriev) This monkey patching makes our custom parser class to be
    # used instead of native.  This affects all subparsers down from
    # 'subparsers' parameter of this function (categories and actions).
    subparsers._parser_class = CategoryParser

    parser = subparsers.add_parser("version")

    parser = subparsers.add_parser("bash-completion")
    parser.add_argument("query_category", nargs="?")

    for category in categories:
        command_object = categories[category]()
        descr = "TODO"
        parser = subparsers.add_parser(
            category, description=descr,
            formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.set_defaults(command_object=command_object)

        category_subparsers = parser.add_subparsers(dest="action")

        for method_name, method in _methods_of(command_object):
            if method is None:
                continue
            method_name = method_name.replace("_", "-")
            parser = category_subparsers.add_parser(
                getattr(method, "alias", method_name),
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description=descr, help=descr)

            action_kwargs = []
            for args, kwargs in getattr(method, "args", []):
                # FIXME(markmc): hack to assume dest is the arg name without
                # the leading hyphens if no dest is supplied
                kwargs.setdefault("dest", args[0][2:])
                action_kwargs.append(kwargs["dest"])
                kwargs["dest"] = "action_kwarg_" + kwargs["dest"]
                parser.add_argument(*args, **kwargs)

            parser.set_defaults(action_fn=method)
            parser.set_defaults(action_kwargs=action_kwargs)
            parser.add_argument("action_args", nargs="*")


def validate_deprecated_args(argv, fn):
    if (len(argv) > 3
       and (argv[2] == fn.__name__)
       and getattr(fn, "deprecated_args", None)):
        for item in fn.deprecated_args:
            if item in argv[3:]:
                LOG.warning("Deprecated argument %s for %s." % (item,
                                                                fn.__name__))


def run(argv, categories):
    parser = lambda subparsers: _add_command_parsers(categories, subparsers)
    category_opt = cfg.SubCommandOpt("category",
                                     title="Command categories",
                                     help="Available categories",
                                     handler=parser)

    CONF.register_cli_opt(category_opt)
    help_msg = ("TODO")

   # CONF.register_cli_opt(cfg.ListOpt("plugin-paths",
   #                                   default=os.environ.get(
   #                                       "RALLY_PLUGIN_PATHS"),
   #                                   help=help_msg))

    try:
        rapi = api.API(config_args=argv[1:], skip_db_check=True)
    except Exception as e:
        print(e)
        return(2)

    if CONF.category.name == "version":
        print(CONF.version)
        return(0)

    fn = CONF.category.action_fn
    fn_args = [encodeutils.safe_decode(arg)
               for arg in CONF.category.action_args]
    # api instance always is the first argument
    fn_args.insert(0, rapi)
    fn_kwargs = {}
    for k in CONF.category.action_kwargs:
        v = getattr(CONF.category, "action_kwarg_" + k)
        if v is None:
            continue
        if isinstance(v, six.string_types):
            v = encodeutils.safe_decode(v)
        fn_kwargs[k] = v

    # call the action with the remaining arguments
    # check arguments
    try:
        validate_args(fn, *fn_args, **fn_kwargs)
    except MissingArgs as e:
        # NOTE(mikal): this isn't the most helpful error message ever. It is
        # long, and tells you a lot of things you probably don't want to know
        # if you just got a single arg wrong.
        print(fn.__doc__)
        CONF.print_help()
        print("Missing arguments:")
        for missing in e.missing:
            for arg in fn.args:
                if arg[1].get("dest", "").endswith(missing):
                    print(" " + arg[0][0])
                    break
        return(1)

    try:
        validate_deprecated_args(argv, fn)

        # skip db check for db and plugin commands
        #if CONF.category.name not in ("db", "plugin"):
        #    rapi.check_db_revision()
        if getattr(fn, "_suppress_warnings", False):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ret = fn(*fn_args, **fn_kwargs)
        else:
            ret = fn(*fn_args, **fn_kwargs)
        return ret

    except Exception:
        raise Exception
