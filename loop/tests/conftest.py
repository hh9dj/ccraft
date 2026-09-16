import pytest

from loop import EventLoop


@pytest.fixture
def event_loop():
    yield EventLoop()
