import argparse
import logging
import sys

from enphase_proxy import __version__
from enphase_proxy.app import load


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="enphase-proxy")

    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="return the version number and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="send verbose output to the console",
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        default=8080,
        type=int,
        help="port number to listen on",
    )
    parser.add_argument(
        "-b",
        "--bind",
        dest="bind",
        default="127.0.0.1",
        type=str,
        help="interface to listen on",
    )

    return parser.parse_args(arguments)


def main() -> int:
    args = parse_arguments(sys.argv[1:])

    logging.basicConfig(
        format="[%(asctime)s] %(levelname)-8s - %(message)s",
        level=logging.DEBUG,
        stream=sys.stdout,
    )

    load().run(
        host=args.bind,
        port=args.port,
        debug=args.verbose,
        use_reloader=False,
    )

    return 0


if __name__ == "__main__":
    main()
