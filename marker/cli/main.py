import sys

from rally.cli import cliutils
from rally.cli.commands import task
from rally.cli.commands import target


def main():
    return cliutils.run(sys.argv, categories)

if __name__ == "__main__":
    sys.exit(main())
