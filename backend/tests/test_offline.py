"""
Offline verification test.
Ensures that the runtime services do not attempt outbound socket connections.
"""

import socket
import pytest


@pytest.fixture(autouse=True)
def block_outbound_network(monkeypatch):
    """
    Blocks all outbound socket connections to enforce offline guarantee.
    Permits only localhost / 127.0.0.1 for local test servers.
    """
    original_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0]
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError(
                f"[SECURITY VIOLATION] Attempted outbound network connection to '{host}'! "
                "The application must run fully offline."
            )
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


def test_offline_enforcement():
    """Verify that any external network call raises an explicit security error."""
    s = socket.socket()
    with pytest.raises(RuntimeError, match="Attempted outbound network connection"):
        s.connect(("8.8.8.8", 53))
