from marker.probes import meta
from marker.server import utils


def itersubclasses(cls, seen=None):
    """Generator over all subclasses of a given class in depth first order.

    NOTE: Use 'seen' to exclude cls which was reduplicated found, because
    cls maybe has multiple super classes of the same probes.
    """

    seen = seen or set()
    try:
        subs = cls.__subclasses__()
    except TypeError:   # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in seen:
            seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, seen):
                yield sub


def configure(name):

    def decorator(probes):
        probes._meta_init()
        try:
            existing_probes = probes.get_base().get(name=name)
        except Exception:
            probes._meta_set("name", name)
        else:
            probes.unregister()
            raise Exception("probes name {0} exist.".format(existing_probes))
        return probes
    return decorator


class BaseProbes(meta.MetaMixin):

    def __init__(self, server_ip, client_ip):
        self.server_ip = server_ip
        self.client_ip = client_ip
        self.data = None

    @classmethod
    def unregister(cls):
        cls._meta_clear()

    @classmethod
    def get(cls, name):
        """Return probes by its name for specified platform.

        :param name: probes's name or fullname
        """
        results = cls.get_all(name=name)

        if not results:
            raise Exception("probes {0} not found.".format(results))

        return results[0]

    @classmethod
    def get_all(cls, name=None):
        """Return all subclass probes of probes.

        All probes that are not configured will be ignored.
        :param name: return only probes with specified name.
        """
        probes = []

        for p in itersubclasses(cls):
            if not issubclass(p, BaseProbes):
                continue
            if not p._meta_is_inited(raise_exc=False):
                continue
            if name and name != p.get_name():
                continue
            probes.append(p)

        return probes

    @classmethod
    def get_name(cls):
        """Return probes's name."""
        return cls._meta_get("name")

    def check_db(self, step, ip):
        raise Exception("'check_db' should be overrided in subclass")

    def run(self, addition):
        raise Exception("'run' should be overrided in subclass")

    def run_as_server(self, addition):
        raise Exception("'run_as_server' should be overrided in subclass")

    def upload_data(self):
        utils.send("data", self.server_ip, data=self.data)
