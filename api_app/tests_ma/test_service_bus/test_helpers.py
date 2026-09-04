from unittest.mock import AsyncMock, MagicMock


class StopReceiveMessages(BaseException):
    pass


def service_bus_client_context():
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def credential_context():
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=MagicMock())
    context.__aexit__ = AsyncMock(return_value=False)
    return context


def queue_receiver_context(*, session=False, receive_messages=False, iterate=False):
    receiver = MagicMock()
    receiver.__aenter__ = AsyncMock(return_value=receiver)
    receiver.__aexit__ = AsyncMock(return_value=False)
    if session:
        receiver.session.session_id = "test_session_id"
    if receive_messages:
        receiver.receive_messages = AsyncMock(return_value=[])
    if iterate:
        receiver.__aiter__.return_value = []
    return receiver
