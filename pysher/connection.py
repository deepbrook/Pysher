import sched
from threading import Thread
from collections import defaultdict
import websocket
import logging
import time
import json


class Connection(Thread):
    def __init__(self, event_handler, url, reconnect_handler=None, log_level=None,
                 daemon=True, reconnect_interval=10, socket_kwargs=None, **thread_kwargs):
        self.event_handler = event_handler
        self.url = url

        self.reconnect_handler = reconnect_handler or (lambda: None)

        self.socket = None
        self.socket_id = ""

        self.event_callbacks = defaultdict(list)

        self.disconnect_called = False
        self.needs_reconnect = False
        self.default_reconnect_interval = reconnect_interval
        self.reconnect_interval = reconnect_interval
        self.socket_kwargs = socket_kwargs or dict()

        self.pong_timer = None
        self.pong_received = False
        self.pong_timeout = 30

        self.bind("pusher:connection_established", self._connect_handler)
        self.bind("pusher:connection_failed", self._failed_handler)
        self.bind("pusher:pong", self._pong_handler)
        self.bind("pusher:ping", self._ping_handler)
        self.bind("pusher:error", self._pusher_error_handler)

        self.state = "initialized"

        self.logger = logging.getLogger(self.__module__)  # create a new logger

        if log_level:
            self.logger.setLevel(log_level)
            if log_level == logging.DEBUG:
                websocket.enableTrace(True)

        # From Martyn's comment at:
        # https://pusher.tenderapp.com/discussions/problems/36-no-messages-received-after-1-idle-minute-heartbeat
        #   "We send a ping every 5 minutes in an attempt to keep connections
        #   alive..."
        # This is why we set the connection timeout to 5 minutes, since we can
        # expect a pusher heartbeat message every 5 minutes.  Adding 5 sec to
        # account for small timing delays which may cause messages to not be
        # received in exact 5 minute intervals.

        self.connection_timeout = 305
        self.connection_timer = None

        self.ping_interval = 120
        self.ping_timer = None

        self.timeout_scheduler = sched.scheduler(
            time.time,
            sleep_max_n(min([self.pong_timeout, self.connection_timeout, self.ping_interval]))
        )
        self.timeout_scheduler_thread = None

        Thread.__init__(self, **thread_kwargs)
        self.daemon = daemon
        self.name = "PysherEventLoop"
    
    def bind(self, event_name, callback, *args, **kwargs):
        """Bind an event to a callback

        :param event_name: The name of the event to bind to.
        :type event_name: str

        :param callback: The callback to notify of this event.
        """
        self.event_callbacks[event_name].append((callback, args, kwargs))

    def disconnect(self, timeout=None):
        self.needs_reconnect = False
        self.disconnect_called = True
        if self.socket:
            self.socket.close()
        self.join(timeout)

    def reconnect(self, reconnect_interval=None):
        if reconnect_interval is None:
            reconnect_interval = self.default_reconnect_interval

        self.logger.info("Connection: Reconnect in %s" % reconnect_interval)
        self.reconnect_interval = reconnect_interval

        self.needs_reconnect = True
        if self.socket:
            self.socket.close()

    def run(self):
        self._connect()

    def _connect(self):
        self.state = "connecting"

        self.socket = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        self.socket.run_forever(**self.socket_kwargs)

        while self.needs_reconnect and not self.disconnect_called:
            self.logger.info("Attempting to connect again in %s seconds."
                             % self.reconnect_interval)
            self.state = "unavailable"
            time.sleep(self.reconnect_interval)

            # We need to set this flag since closing the socket will set it to
            # false
            self.socket.keep_running = True
            self.socket.run_forever(**self.socket_kwargs)

    def _on_open(self):
        self.logger.info("Connection: Connection opened")
                
        # Send a ping right away to inform that the connection is alive. If you
        # don't do this, it takes the ping interval to subcribe to channel and
        # events
        self.send_ping()
        self._start_timers()

    def _on_error(self, error):
        self.logger.info("Connection: Error - %s" % error)
        self.state = "failed"
        self.needs_reconnect = True

    def _on_message(self, message):
        self.logger.info("Connection: Message - %s" % message)

        # Stop our timeout timer, since we got some data
        self._stop_timers()

        params = self._parse(message)

        if 'event' in params.keys():
            if 'channel' not in params.keys():
                # We've got a connection event.  Lets handle it.
                if params['event'] in self.event_callbacks.keys():
                    for func, args, kwargs in self.event_callbacks[params['event']]:
                        try:
                            func(params['data'], *args, **kwargs)
                        except Exception:
                            self.logger.exception("Callback raised unhandled")
                else:
                    self.logger.info("Connection: Unhandled event")
            else:
                # We've got a channel event.  Lets pass it up to the pusher
                # so it can be handled by the appropriate channel.
                self.event_handler(
                    params['event'],
                    params['data'],
                    params['channel']
                )

        # We've handled our data, so restart our connection timeout handler
        self._start_timers()

    def _on_close(self, *args):
        self.logger.info("Connection: Connection closed")
        self.state = "disconnected"
        self._stop_timers()

    @staticmethod
    def _parse(message):
        return json.loads(message)

    def _stop_timers(self):
        for event in self.timeout_scheduler.queue:
            self._cancel_scheduler_event(event)

    def _start_timers(self):
        self._stop_timers()

        self.ping_timer = self.timeout_scheduler.enter(self.ping_interval, 1, self.send_ping, argument=())
        self.connection_timer = self.timeout_scheduler.enter(self.connection_timeout, 2, self._connection_timed_out,
                                                             argument=())

        if not self.timeout_scheduler_thread:
            self.timeout_scheduler_thread = Thread(target=self.timeout_scheduler.run, daemon=True, name="PysherScheduler")
            self.timeout_scheduler_thread.start()

        elif not self.timeout_scheduler_thread.is_alive():
            self.timeout_scheduler_thread = Thread(target=self.timeout_scheduler.run, daemon=True, name="PysherScheduler")
            self.timeout_scheduler_thread.start()

    def _cancel_scheduler_event(self, event):
        try:
            self.timeout_scheduler.cancel(event)
        except ValueError:
            self.logger.info('Connection: Scheduling event already cancelled')

    def send_event(self, event_name, data, channel_name=None):
        """Send an event to the Pusher server.

        :param str event_name:
        :param Any data:
        :param str channel_name:
        """
        event = {'event': event_name, 'data': data}
        if channel_name:
            event['channel'] = channel_name

        self.logger.info("Connection: Sending event - %s" % event)
        try:
            self.socket.send(json.dumps(event))
        except Exception as e:
            self.logger.error("Failed send event: %s" % e)

    def send_ping(self):
        self.logger.info("Connection: ping to pusher")
        try:
            self.socket.send(json.dumps({'event': 'pusher:ping', 'data': ''}))
        except Exception as e:
            self.logger.error("Failed send ping: %s" % e)

        self.pong_timer = self.timeout_scheduler.enter(self.pong_timeout, 3, self._check_pong, argument=())

    def send_pong(self):
        self.logger.info("Connection: pong to pusher")
        try:
            self.socket.send(json.dumps({'event': 'pusher:pong', 'data': ''}))
        except Exception as e:
            self.logger.error("Failed send pong: %s" % e)

    def _check_pong(self):
        self._cancel_scheduler_event(self.pong_timer)

        if self.pong_received:
            self.pong_received = False
        else:
            self.logger.info("Did not receive pong in time.  Will attempt to reconnect.")
            self.state = "failed"
            self.reconnect()

    def _connect_handler(self, data):
        parsed = json.loads(data)
        self.socket_id = parsed['socket_id']
        self.state = "connected"

        if self.needs_reconnect:

            # Since we've opened a connection, we don't need to try to reconnect
            self.needs_reconnect = False

            self.reconnect_handler()

            self.logger.debug('Connection: Establisheds reconnection')
        else:
            self.logger.debug('Connection: Establisheds first connection')

    def _failed_handler(self, data):
        self.state = "failed"

    def _ping_handler(self, data):
        self.send_pong()
        # Restart our timers since we received something on the connection
        self._start_timers()

    def _pong_handler(self, data):
        self.logger.info("Connection: pong from pusher")
        self.pong_received = True

    def _pusher_error_handler(self, data):
        if 'code' in data:

            try:
                error_code = int(data['code'])
            except:
                error_code = None

            if error_code is not None:
                self.logger.error("Connection: Received error %s" % error_code)

                if (error_code >= 4000) and (error_code <= 4099):
                    # The connection SHOULD NOT be re-established unchanged
                    self.logger.info("Connection: Error is unrecoverable.  Disconnecting")
                    self.disconnect()
                elif (error_code >= 4100) and (error_code <= 4199):
                    # The connection SHOULD be re-established after backing off
                    self.reconnect()
                elif (error_code >= 4200) and (error_code <= 4299):
                    # The connection SHOULD be re-established immediately
                    self.reconnect(0)
                else:
                    pass
            else:
                self.logger.error("Connection: Unknown error code")
        else:
            self.logger.error("Connection: No error code supplied")

    def _connection_timed_out(self):
        self.logger.info("Did not receive any data in time.  Reconnecting.")
        self.state = "failed"
        self.reconnect()


def sleep_max_n(max_sleep_time):
    def sleep(time_to_sleep):
        time.sleep(min(max_sleep_time, time_to_sleep))
    return sleep
