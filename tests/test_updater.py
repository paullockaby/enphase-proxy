from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from enphase_proxy.updater import CredentialsManager, FetchedCredentials


@pytest.fixture
def credentials_manager() -> CredentialsManager:
    return CredentialsManager(  # noqa: S106
        url="https://example.com/",
        username="test_username",
        password="test_password",
        serialno="test_serialno",
        jwt="test_jwt",
    )


@pytest.fixture
def test_credentials():
    manager = CredentialsManager()
    manager.data = FetchedCredentials(  # noqa: S106
        fetched_at=datetime.now() - timedelta(hours=1),
        expires_at=datetime.now() + timedelta(hours=1),
        token="old_token",
    )
    return manager


def test_init(credentials_manager: CredentialsManager):
    assert credentials_manager.enphase_url == "https://example.com/"
    assert credentials_manager.enphase_username == "test_username"
    assert credentials_manager.enphase_password == "test_password"  # noqa: S105
    assert credentials_manager.enphase_serialno == "test_serialno"
    assert credentials_manager.enphase_jwt == "test_jwt"
    assert credentials_manager.data is None


@patch.object(CredentialsManager, "_fetch_credentials")
@pytest.mark.asyncio
async def test_credentials_use_locally_provided_token(
    mock_fetch_credentials: MagicMock, credentials_manager: CredentialsManager
):
    assert await credentials_manager.credentials == "test_jwt"
    mock_fetch_credentials.assert_not_called()


@patch.object(CredentialsManager, "_fetch_credentials")
@pytest.mark.asyncio
async def test_credentials_fetch_new_credentials(
    mock_fetch_credentials: MagicMock, credentials_manager: CredentialsManager
):
    credentials_manager.enphase_jwt = None
    mock_fetch_credentials.return_value = FetchedCredentials(  # noqa: S106
        fetched_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
        token="new_token",
    )
    assert await credentials_manager.credentials == "new_token"
    mock_fetch_credentials.assert_called_once()


@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
@pytest.mark.asyncio
async def test_fetch_credentials(mock_get: MagicMock, mock_post: MagicMock, credentials_manager: CredentialsManager):
    session_id = "session_id"
    jwt_data: dict = {
        "generation_time": datetime.now().timestamp(),
        "expires_at": (datetime.now() + timedelta(hours=1)).timestamp(),
        "token": "new_token",
    }

    mock_post.return_value.json = MagicMock(return_value={"session_id": session_id})
    mock_post.return_value.raise_for_status = MagicMock()
    mock_get.return_value.json = MagicMock(return_value=jwt_data)
    mock_get.return_value.raise_for_status = MagicMock()

    credentials_data = await credentials_manager._fetch_credentials()

    mock_post.assert_called_once()
    mock_get.assert_called_once()
    assert credentials_data.fetched_at == datetime.fromtimestamp(jwt_data["generation_time"])
    assert credentials_data.expires_at == datetime.fromtimestamp(jwt_data["expires_at"])
    assert credentials_data.token == jwt_data["token"]


@patch.object(CredentialsManager, "_fetch_credentials")
@pytest.mark.asyncio
async def test_credentials_expiry(mock_fetch_credentials: MagicMock):
    starting_timestamp = datetime.now()
    manager = CredentialsManager()

    # current token expired one hour ago
    manager.data = FetchedCredentials(  # noqa: S106
        fetched_at=starting_timestamp - timedelta(hours=10),
        expires_at=starting_timestamp - timedelta(hours=1),
        token="old_token",
    )

    # new credential expires in one hour
    mock_fetch_credentials.return_value = FetchedCredentials(  # noqa: S106
        fetched_at=starting_timestamp,
        expires_at=starting_timestamp + timedelta(hours=1),
        token="new_token",
    )

    credentials = await manager.credentials
    assert credentials == "new_token"
    assert manager.data.fetched_at == starting_timestamp
    assert manager.data.expires_at == starting_timestamp + timedelta(hours=1)
    assert mock_fetch_credentials.call_count == 1


@patch.object(CredentialsManager, "_fetch_credentials")
@pytest.mark.asyncio
async def test_credentials_fetch(mock_fetch_credentials: MagicMock):
    starting_timestamp = datetime.now()
    manager = CredentialsManager()

    # current token expires in an hour
    manager.data = FetchedCredentials(  # noqa: S106
        fetched_at=starting_timestamp - timedelta(hours=10),
        expires_at=starting_timestamp + timedelta(hours=1),
        token="old_token",
    )

    # this is a new token but we're not going to end up with it
    mock_fetch_credentials.return_value = FetchedCredentials(  # noqa: S106
        fetched_at=starting_timestamp,
        expires_at=starting_timestamp + timedelta(hours=10),
        token="new_token",
    )

    credentials = await manager.credentials
    assert credentials == "old_token"
    assert manager.data.fetched_at == starting_timestamp - timedelta(hours=10)
    assert manager.data.expires_at == starting_timestamp + timedelta(hours=1)
    assert mock_fetch_credentials.call_count == 0
