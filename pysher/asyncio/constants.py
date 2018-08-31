from collections import deque


#: Channel name we give messages that do not have a `channel` field attached
# to them. This allows clients to write callbacks for system messages.
SYSTEM_CHANNEL = 'system'

#: Sentinel value to signal channels to exit.
SIG_SHUTDOWN = 'shutdown'


class ConnectionState:
    """State object for pusher states.

    Wraps a python deque of length 3, where the zero index is the current state.

    Reference:

        https://pusher.com/docs/client_api_guide/client_connect#available-states

    """

    #: The websocket was instantiated, but the connecting sequence hasn't started.
    INITIALIZED = 'initialized'

    #: The websocket is connected to the pusher services
    CONNECTED = 'connected'

    #: We currently cannot access pusher services; the wss connection is active, however.
    UNAVAILABLE = 'unavailable'

    #: There was an error while communicating with pusher services.
    FAILED = 'connection_failed'

    #: We were disconnected from pusher by the server.
    DISCONNECTED = 'disconnected'

    #: The websocket was closed, either actively, or due a network or protocol error
    CONNECTION_CLOSED = 'connection_closed'

    __all__ = [
        INITIALIZED,
        CONNECTED,
        UNAVAILABLE,
        FAILED,
        DISCONNECTED,
        CONNECTION_CLOSED,
    ]

    def __init__(self):
        self._state_history = deque([self.INITIALIZED], maxlen=3)

    def current(self):
        return self._state_history[0]

    def is_available(self):
        return self._state_history[0] is self.CONNECTED

    def update(self, new_state):
        if new_state not in ConnectionState.__all__:
            raise ValueError("New state must be valid member of ConnectionState class!")
        self._state_history.append(new_state)
        return new_state

    @property
    def history(self):
        return self._state_history