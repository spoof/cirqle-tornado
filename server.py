#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import sys
import logging
import signal

import tornado.ioloop
import tornado.web
import tornado.httpserver
from tornado.options import define, options

import handlers  # noqa
from route import route
from amysql import AsyncMysql
from settings import DATABASE, DEBUG, SERVER_PORT


log = logging.getLogger('cirqle')


class Application(tornado.web.Application):

    def __init__(self):
        api_handlers = route.handlers()

        settings = dict(
            debug=DEBUG
        )
        tornado.web.Application.__init__(self, api_handlers, **settings)

        self._db = AsyncMysql(host=DATABASE['host'], db=DATABASE['database'],
                              user=DATABASE['user'],
                              password=DATABASE['password'], pool_size=5,
                              time_zone='+4:00')

    @property
    def db(self):
        return self._db


def install_signal_handlers(server):

    def request_force_stop(signum, frame):
        log.warning('Forced stop requested.')
        ioloop_stop(server)

    def request_stop(signum, frame):
        log.warning('Graceful stop requested.')
        server.stop()

        signal.signal(signal.SIGINT, request_force_stop)
        signal.signal(signal.SIGTERM, request_force_stop)

        ioloop_stop(server)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)


def ioloop_stop(server):
    tornado.ioloop.IOLoop.instance().stop()
    server.request_callback.db.stop()

    log.warning('Server is stopped')
    sys.exit(0)


if __name__ == "__main__":

    define('port', help='bind server on the given port', type=int,
           default=SERVER_PORT)
    tornado.options.parse_command_line()
    app = Application()

    server = tornado.httpserver.HTTPServer(app, xheaders=True)
    install_signal_handlers(server)

    try:
        server.listen(options.port)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        ioloop_stop(server)
