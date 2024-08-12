from unittest import mock

from enphase_proxy import __main__


def test_main_no_arguments():
    with mock.patch.object(__main__, "load") as mock_load:
        mock_app = mock.MagicMock()
        mock_load.return_value = mock_app

        __main__.main()
        mock_app.run.assert_called_once_with(host="127.0.0.1", port=8080, debug=False, use_reloader=False)


def test_main_with_arguments():
    with mock.patch.object(__main__, "load") as mock_load:
        mock_app = mock.MagicMock()
        mock_load.return_value = mock_app

        __main__.main("--verbose", "--port", "8000", "--bind", "0.0.0.0")  # noqa: S104
        mock_app.run.assert_called_once_with(host="0.0.0.0", port=8000, debug=True, use_reloader=False)  # noqa: S104
