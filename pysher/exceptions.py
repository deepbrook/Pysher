"""Python representations of Pusher Error codes and other exceptions

Reference:

    https://pusher.com/docs/pusher_protocol#error-codes

"""


class PusherException(Exception):
    """General exception class for pusher error codes."""
    def __init__(self, code, description):
        self.code = code
        self.description = description
        self.message = "Error {}: {}".format(code, description)
        super(PusherException, self).__init__(self.message)


class PusherServiceUnavailable(PusherException):
    def __init__(self, pusher_state, websocket_state):
        self.pusher_state = pusher_state
        self.ws_state = websocket_state
        descr = "We're currently unable to communicate with the pusher service! " \
                "Pusher Connection: {}, Websocket Connection: {}!"
        super(PusherServiceUnavailable, self).__init__(code=1, description=descr.format(pusher_state, websocket_state))


class PusherConnectionError(PusherException):
    """Indicate a critical error of which cannot be solved via a reconnect.

    Covered error codes:

        4000-4099

    """


class ReconnectRequired(Exception):
    """Indicate critical error which require a reconnect to resolve.

    Covered error codes:

        4100-4199 (reconnect after a few seconds)
        4200-4299 (immediate reconnect)

    """

    def __init__(self, after=0):
        """Initialize a class instance.

        :param int after: time in seconds to wait before reconnecting.
        """
        self.after = after
        self.message = "Reconnect required! Reconnection recommended in {}s!".format(after)


class ReconnectRequiredLater(ReconnectRequired):
    def __init__(self, after=2):
        super(ReconnectRequiredLater, self).__init__(after)


class PusherClientError(Exception):
    """Indicate errors raised by the client side."""
