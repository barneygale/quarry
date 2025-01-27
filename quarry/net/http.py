import json

from twisted.internet import defer, reactor
from twisted.internet.defer import succeed
from twisted.python import failure
from twisted.web.client import Agent, error, Response, readBody
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implementer


class HTTPException(Exception):
    def __init__(self, error_type, error_message):
        self.error_type = error_type
        self.error_message = error_message

    def __str__(self):
        return "%s: %s" % (self.error_type, self.error_message)


@implementer(IBodyProducer)
class BytesProducer:
    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


def request(url, timeout, err_type=Exception, expect_content=False, data=None):
    d0 = defer.Deferred()

    def _callback(response):
        def _callback2(body):
            if expect_content:
                if len(body) == 0 or response.code == 204:
                    err = failure.Failure(err_type(
                        "No Content",
                        f"No content was returned by the server for the url {url}"))
                    d0.errback(err)
            if len(body):
                d0.callback(json.loads(body.decode('ascii')))
            else:
                d0.callback(None)
        d = readBody(response)
        d.addCallback(_callback2)
        return d

    def _errback(err):
        if isinstance(err.value, error.Error):
            if err.value.status == b"204":
                if expect_content:
                    err = failure.Failure(err_type(
                        "No Content",
                        f"No content was returned by the server for the url {url}"))
                else:
                    d0.callback(None)
                    return
            else:
                data = json.loads(err.value.response.decode('ascii'))
                err = failure.Failure(err_type(
                    data['error'],
                    data['errorMessage']))
        d0.errback(err)

    agent = Agent(reactor)

    if data:
        d1 = agent.request(
            b'POST',
            url,
            Headers({"Content-Type": ["application/json"]}),
            BytesProducer(json.dumps(data).encode('ascii')),
        )
    else:
        d1 = agent.request(b'GET', url)

    d1.addCallbacks(_callback, _errback)

    return d0
