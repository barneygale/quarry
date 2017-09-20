from twisted.internet.task import LoopingCall


class Task(object):
    ticker = None

    def stop(self):
        self.ticker._tasks.remove(self)


class LoopTask(Task):
    def __init__(self, ticker, interval, callback):
        self.ticker = ticker
        self.interval = interval
        self.callback = callback

    def update(self):
        if self.ticker.tick % self.interval == 0:
            self.callback()


class DelayTask(Task):
    def __init__(self, ticker, delay, callback):
        self.ticker = ticker
        self.delay = delay
        self.callback = callback
        self.restart()

    def restart(self):
        self.target = self.ticker.tick + self.delay

    def update(self):
        if self.ticker.tick >= self.target:
            self.callback()
            self.stop()


class Ticker(object):
    #: The current tick
    tick = 0

    #: Interval between ticks, in seconds
    interval = 1.0/20

    #: Maximum number of delayed ticks before they're all skipped
    max_lag = 40

    def __init__(self, logger):
        self._logger = logger
        self._tasks = []
        self._impl = LoopingCall.withCount(self._update)

    def start(self):
        """
        Start running the tick loop.
        """
        self._impl.start(self.interval, now=False)

    def stop(self):
        """
        Stop running the tick loop.
        """
        self._impl.stop()

    def add_loop(self, interval, callback):
        """
        Repeatedly run a callback.

        :param interval: The interval in ticks
        :param callback: The callback to run
        :return: An instance providing a ``stop()`` method
        """
        task = LoopTask(self, interval, self._wrap(callback))
        self._tasks.append(task)
        return task

    def add_delay(self, delay, callback):
        """
        Run a callback after a delay.

        :param delay: The delay in ticks
        :param callback: The callback to run
        :return: An instance providing ``stop()`` and ``restart()`` methods
        """
        task = DelayTask(self, delay, self._wrap(callback))
        self._tasks.append(task)
        return task

    def _update(self, count):
        if count >= self.max_lag:
            self._logger.warn("Can't keep up! Skipping %d ticks" % (count - 1))
            count = 1

        for _ in range(count):
            for task in list(self._tasks):
                task.update()
            self.tick += 1

    def _wrap(self, callback):
        def fn():
            try:
                callback()
            except Exception, e:
                self._logger.exception(e)
        return fn