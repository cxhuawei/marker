import sys

from marker.cli import cliutils
from marker.cli.commands import service
from marker.cli.commands import task
from marker.cli.commands import target


categories = {
    "service": service.ServiceCommands,
    "task": task.TaskCommands,
    "target": target.TargetCommands
}


def main():
    return cliutils.run(sys.argv, categories)


if __name__ == "__main__":
    sys.exit(main())
