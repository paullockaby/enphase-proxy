import argparse
import logging
import sys

from enphase import __version__
from enphase.proxy.app import load

if __name__ == "__main__":
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
    args = parser.parse_args()

    # send application logs to stdout
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)-8s - %(message)s",
        level=logging.DEBUG,
        stream=sys.stdout,
    )

    # send access logs to stderr and do not propagate them to the root logger
    access_logger = logging.getLogger("werkzeug")
    access_logger.addHandler(logging.StreamHandler(stream=sys.stderr))
    access_logger.propagate = False

    # run only on localhost for testing
    load().run(host="127.0.0.1", port=8080, debug=args.verbose, use_reloader=False)
