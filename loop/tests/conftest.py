import os
import socket

import pytest

from loop import EventLoop


@pytest.fixture
def event_loop():
    yield EventLoop()


@pytest.fixture
def socket_pair():
    s1, s2 = socket.socketpair()
    s1.setblocking(False)
    s2.setblocking(False)

    yield s1, s2

    s1.close()
    s2.close()


@pytest.fixture
def pipe():
    read_fd, write_fd = os.pipe()

    os.set_blocking(read_fd, False)
    os.set_blocking(write_fd, False)

    yield read_fd, write_fd

    os.close(read_fd)
    os.close(write_fd)
