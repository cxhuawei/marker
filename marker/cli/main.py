import sys

from rally.cli import cliutils
from rally.cli.commands import task
from rally.cli.commands import target


categories = {
    "task": task.TaskCommands,
    "target": target.TargetCommands
}

def main():
    return cliutils.run(sys.argv, categories)

if __name__ == "__main__":
    sys.exit(main())
