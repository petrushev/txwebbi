from os.path import join as pathjoin
from os.path import dirname

from werkzeug.routing import Rule, Map

from twisted.internet import reactor

from txwebby import bootstrapWebServer, bootstrapCommonFrontHandler

from twisted.internet.task import deferLater
from twisted.python import log

import controllers

template_path = pathjoin(dirname(__file__), 'templates/')

url_map = Map([
    Rule('/', endpoint = controllers.Index),
    Rule('/log', endpoint = controllers.Log)
])

BaseFrontHandler = bootstrapCommonFrontHandler(url_map, template_path, controllers.NotFound)

class FrontHandler(BaseFrontHandler):
    """Extended FrontHandler to accomodate prompting of requests to factory's sentinel"""

    def process(self):
        BaseFrontHandler.process(self)

        # defer task of prompting
        init_task = deferLater(reactor, 0, self.prompt)
        init_task.addErrback(self.process_err)

    def process_err(self, reason):
        log.err('prompt start err: '+ reason.getErrorMessage())

    def prompt(self):
        """Send prompt to each log in the factory's sentinel"""
        factory = self.channel.factory
        if not hasattr(factory, 'sentinel'):
            factory.sentinel = set()

        for logCtrl in factory.sentinel:
            if self.controller == logCtrl: continue

            init_task = deferLater(reactor, 0, logCtrl.prompt, self)
            init_task.addErrback(self.prompt_err)

    def prompt_err(self, reason):
        log.err('log prompt err: '+ reason.getErrorMessage())

WebServer = bootstrapWebServer(FrontHandler)

# the following 3 lines are needed in case we use the `twistd` infrastructure:
# twistd -ny main.py
from twisted.application.service import Application
application = Application('The Web')
WebServer(port = 8070).setServiceParent(application)

if __name__=='__main__':
    reactor.callLater(0, WebServer(port = 8070).startService)
    reactor.run()
