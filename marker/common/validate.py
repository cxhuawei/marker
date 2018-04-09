import os


def validate_port(port):
    command = "lsof -i:{0}".format(port)
    if os.system(command):
        return False
    else:
        return True
