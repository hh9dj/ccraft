import time

from loop import EventLoop

if __name__ == "__main__":
    loop = EventLoop()
    start = time.monotonic()

    def trampoline():
        elapsed = time.monotonic() - start
        print(f"trampoline tick {elapsed:.1f}s")
        loop.call_later(0.2, trampoline)

    loop.call_soon(trampoline)
    loop.call_later(8, loop.stop)
    loop.run_forever()
