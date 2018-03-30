import json

from twisted.internet import defer
from twisted.web import client, error
from twisted.python import failure

client.HTTPClientFactory.noisy = False


class HTTPException(Exception):
    def __init__(self, error_type, error_message):
        self.error_type = error_type
        self.error_message = error_message

    def __str__(self):
        return "%s: %s" % (self.error_type, self.error_message)


def request(url, timeout, err_type=Exception, expect_content=False, data=None):
    d0 = defer.Deferred()

    def _callback(data):
        d0.callback(json.loads(data.decode('ascii')))

    def _errback(err):
        if isinstance(err.value, error.Error):
            if err.value.status == b"204":
                if expect_content:
                    err = failure.Failure(err_type(
                        "No Content",
                        "No content was returned by the server"))
                else:
                    d0.callback(None)
                    return
            else:
                data = json.loads(err.value.response.decode('ascii'))
                err = failure.Failure(err_type(
                    data['error'],
                    data['errorMessage']))
        d0.errback(err)

    if data:
        d1 = client.getPage(
            url,
            headers={b'Content-Type': b'application/json'},
            method=b'POST',
            postdata=json.dumps(data).encode('ascii'))
    else:
        d1 = client.getPage(url)
    d1.addCallbacks(_callback, _errback)

    return d0
