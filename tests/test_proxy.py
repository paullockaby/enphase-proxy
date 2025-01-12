import argparse

from enphase_proxy import __main__


def test_main_no_arguments():
    result = __main__.parse_arguments([])
    assert result == argparse.Namespace(verbose=False, port=8080, bind="127.0.0.1")


def test_main_with_arguments():
    result = __main__.parse_arguments(["--port", "8000", "--bind", "1.1.1.1", "--verbose"])
    assert result == argparse.Namespace(verbose=True, port=8000, bind="1.1.1.1")
