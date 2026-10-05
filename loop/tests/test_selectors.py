import os
import socket

import pytest

from loop.loop import EventLoop


def test_reader_ready(event_loop: EventLoop, pipe: tuple[int, int]):
    read_fd, write_fd = pipe

    output = b""
    excepted = b"READ!"

    def echo(file_d):
        nonlocal output
        output = os.read(file_d, 8)
        event_loop.remove_reader(file_d)

    event_loop.add_reader(read_fd, echo, read_fd)
    event_loop.call_later(0.1, os.write, write_fd, excepted)

    event_loop.run_forever()

    assert output == excepted


def test_writer_ready(event_loop: EventLoop, pipe: tuple[int, int]):
    read_fd, write_fd = pipe

    while True:
        try:
            os.write(write_fd, b"x" * 65536)
        except BlockingIOError:
            break

    fired = False

    def write_fired():
        nonlocal fired
        fired = True
        event_loop.remove_writer(write_fd)

    event_loop.add_writer(write_fd, write_fired)

    # free-up some space on the pipe buffer to triger the write cb
    event_loop.call_later(0.1, os.read, read_fd, 4096)

    event_loop.run_forever()

    assert fired == True


def test_unregister_read(event_loop: EventLoop, pipe: tuple[int, int]):
    read_fd, write_fd = pipe
    output = b""
    excepted = b"READ!"

    def echo(file_d):
        nonlocal output
        output = os.read(file_d, 8)
        event_loop.remove_reader(file_d)

    event_loop.add_reader(read_fd, echo, read_fd)
    event_loop.call_later(0.1, os.write, write_fd, excepted)
    event_loop.remove_reader(read_fd)
    event_loop.run_forever()
    assert output == b""


def test_unregister_write(event_loop: EventLoop, pipe: tuple[int, int]):
    _, write_fd = pipe
    fired = False

    def write_fired():
        nonlocal fired
        fired = True
        event_loop.remove_writer(write_fd)

    event_loop.add_writer(write_fd, write_fired)
    event_loop.remove_writer(write_fd)

    event_loop.run_forever()

    assert fired == False


def test_duplicate_register(event_loop: EventLoop, pipe: tuple[int, int]):
    read_fd, writer_fd = pipe
    event_loop.add_reader(read_fd, lambda _: None, None)
    event_loop.add_writer(writer_fd, lambda _: None, None)

    with pytest.raises(KeyError):
        event_loop.add_reader(read_fd, lambda _: None, None)
    with pytest.raises(KeyError):
        event_loop.add_writer(writer_fd, lambda _: None, None)


def test_duplicate_unregister(event_loop: EventLoop, pipe: tuple[int, int]):
    read_fd, write_fd = pipe

    event_loop.add_reader(read_fd, lambda _: None, None)
    event_loop.remove_reader(read_fd)

    event_loop.add_writer(write_fd, lambda _: None, None)
    event_loop.remove_writer(write_fd)

    with pytest.raises(KeyError):
        event_loop.remove_reader(read_fd)
    with pytest.raises(KeyError):
        event_loop.remove_writer(write_fd)


def test_read_write_same_fd(
    event_loop: EventLoop, socket_pair: tuple[socket.socket, socket.socket]
):
    s1, s2 = socket_pair

    readable = writable = False

    # add reader / writer on same socket
    def write_ready():
        event_loop.remove_writer(s1.fileno())

        nonlocal writable
        writable = True

    def read_ready():
        event_loop.remove_reader(s1.fileno())

        nonlocal readable
        readable = True

    event_loop.add_writer(s1.fileno(), write_ready)

    event_loop.add_reader(s1.fileno(), read_ready)
    s2.send(b"hello")

    event_loop.run_forever()

    assert readable == True
    assert writable == True
