===================
Marker Architecture
===================

The Command of marker
=======================
# start server
marker server start --ip ip --port port
# start fping
marker start fping
# add the monitor's targets
marker targets add --ip ip1,ip2,ip3
marker report get

BaseMarker is marker's core class. all kinds of marker should implement
BaseMarker. The BaseMarker have two executing functions: mark(), mark_fork().
The subclass should be override the executin function(the concurrent command
should override mark_fork function, the others commands should override
mark function).

.. code-block:: python

    class BaseMarker:

        def __init__(self, step)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            (self, step):
            self.step = step

        def mark():
            pass

        def mark_fork():
            pass

        def get_command():
            """Ths subclasses should implements this function"""
            Pass


    class NetMarker(BaseMarker):

        def __init__(self, step, offsets, pings):
            super(NetMarker, self).__init__(step)
            self.offsets = offsets
            self.pings = pings

        def add_targets(self, hosts):
            pass

    class CpuMarker(BaseMarker):

        # TODO(Hai Shi): I am not sure what we need in CpuMarker
        def __init__(self, step):
            super(CpuMarker, self).__init__(step)


Command is a tool class. This tool class combine subcommands.

.. code-block:: python

    class Command:
    ...
    def __init__(self, command):
        self.subcommands = [command]

    def add_param(self, key, value):
        self.subcommands.append(str(key))

        if value is not None:
            slef.subcommands.append(value)

    def make():
        return " ".join(self.subcommands)
    ...

The rest_api should should be ``marker.api.v1``. the server's main function
should be in ``marker.app``.

The ``marker.app``'s code looks like:

.. code-block:: python

    import flask
    from marker.api.v1 import data
    from oss_lib import routing

    app = flask.Flask("marker")

    for bp in [data]:
        for url_prefix, blueprint in bp.get_blueprints():
            app.register_blueprint(blueprint, url_prefix="/api/v1/%s"
            % url_prefix)

    app = routing.add_routing_map(app, html_uri=None, json_uri="/")

``The marker.api.v1.data``'s code looks like:

.. code-block:: python

    import flask

    bp = flask.blueprint("data")

    bp.route("/data")
    get data():
        pass
        return data

    sub get_blueprint():
        return [["data", bp]]
