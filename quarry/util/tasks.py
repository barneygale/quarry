from twisted.internet import reactor
from twisted.internet.task import LoopingCall

class Tasks(object):
    def __init__(self):
        self._tasks = []

    def add_loop(self, time, callback, *args):
        task = LoopingCall(callback, *args)
        task.start(time, now=False)
        self._tasks.append(task)
        return task

    def add_delay(self, time, callback, *args):
        task = reactor.callLater(time, callback, *args)
        def stop():
            if task.active():
                task.cancel()
        def restart():
            if task.active():
                task.reset(time)
        task.restart = restart
        task.stop = stop
        self._tasks.append(task)
        return task

    def stop_all(self):
        while len(self._tasks) > 0:
            task = self._tasks.pop(0)
            task.stop()