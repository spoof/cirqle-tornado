# -*- coding: utf-8 -*-
import tornado.web


class route(object):
    '''
    Decorates RequestHandlers and builds up a list of routables handlers.

    Here is a simple "Hello, world" example app::

        import tornado.ioloop
        import tornado.web

        from route import route

        @route('/')
        class HomepageHandler(tornado.web.RequestHandler):
            def get(self):
                self.write('<a href="/say/hello">Click here</a>')

        @route('/say/hello')
        class HelloHandler(tornado.web.RequestHandler):
            def get(self):
                self.write('Hello, world!')

        if __name__ == '__main__':
            application = tornado.web.Application(route.handlers())
            application.listen(8888)
            tornado.ioloop.IOLoop.instance().start()
    '''
    _routes = []

    def __init__(self, uri, name=None):
        self._uri = uri
        self.name = name

    def __call__(self, handler):
        '''Gets called when we decorate a class.'''
        name = self.name and self.name or handler.__name__
        self._routes.append(tornado.web.url(self._uri, handler, name=name))
        return handler

    @classmethod
    def handlers(self):
        return self._routes


def route_redirect(from_url, to_url, name=None):
    route._routes.append(tornado.web.url(from_url, tornado.web.RedirectHandler,
                                         {'url': to_url}, name=name))
