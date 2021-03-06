import json
import socket
from marker.common import logging


LOG = logging.getLogger(__name__)


def send(action, target, port=9999, data=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((target, port))
    except Exception as e:
        LOG.warning(e)
        LOG.warning("There is no marker service on {0}:{1}".format(
            target, port))
        return 1
    sock.sendall(json.dumps({"action": action, "data": data,
                             "target": target}))
    LOG.info("option: send. \naction: {0}. \ndata: {1}. \n"
             "target: {2}. ".format(str(action), str(data), str(target)))
    sock.close()
