from twisted.internet import reactor

class Timer:
    task = None
    def __init__(self, time, callback):
        self.time = time
        self.callback = callback

    def start(self):
        self.task = reactor.callLater(self.time, self.callback)

    def reset(self):
        if self.task.active():
            self.task.reset(self.time)

    def stop(self):
        if self.task.active():
            self.task.cancel()