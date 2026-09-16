from loop import EventLoop

if __name__ == "__main__":
    loop = EventLoop()

    def test():
        print("testing")
        loop.run_forever()

    loop.call_soon(print, "hello you")
    loop.call_soon(test)
    loop.call_soon(print, "this is your event loop :)")
    loop.run_forever()

    print("done :(")
