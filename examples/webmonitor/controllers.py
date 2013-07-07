from datetime import datetime

from twisted.web.http import NOT_FOUND, TEMPORARY_REDIRECT
from twisted.internet import reactor

from txwebbi import BaseController

class NotFound(BaseController):
    def init(self):
        self.request.setResponseCode(NOT_FOUND)
        self.request.write('page not found. [404]')
        self.finish()

class Index(BaseController):
    def init(self):
        self.request.write('Hello! This request will be logged.')
        self.finish()

class Log(BaseController):
    def init(self):
        # the factory object holds persistant info through different web requests
        factory = self.request.channel.factory
        if not hasattr(factory, 'sentinel'):
            factory.sentinel = set() # sentinel will be a set of Log controllers

        # add this log controller to the factory's sentinel
        factory.sentinel.add(self)

    def prompt(self, frontHandler):
        # on each request, the prompt method of each controller in the factory's sentinel should be called
        # the easiest way to achieve this is to add a deferred on the BaseController __init__
        # or to attach a hook after the front handler process starts
        self.request.write('%s %s <br/>\n' % \
                           (frontHandler.method, frontHandler.path))

    def notifyDisconnect(self, reason):
        # remove this log controller from the factory's sentinel
        factory = self.request.channel.factory
        if self in factory.sentinel:
            factory.sentinel.remove(self)
