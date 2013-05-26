from os.path import join as pathjoin
from os.path import dirname

from werkzeug.routing import Rule, Map

from txwebby import bootstrapWebServer, bootstrapCommonFrontHandler

import controllers

template_path = pathjoin(dirname(__file__), 'templates/')

url_map = Map([
    Rule('/', endpoint = controllers.Index),
    Rule('/form', endpoint = controllers.Form),
    Rule('/report', endpoint = controllers.Report, methods=['GET']),
    Rule('/report', endpoint = controllers.PostReport, methods=['POST']),
    Rule('/error', endpoint = controllers.ErrorPage),
])

FrontHandler = bootstrapCommonFrontHandler(url_map, template_path, controllers.NotFound)

WebServer = bootstrapWebServer(FrontHandler)

# the following 3 lines are needed in case we use the `twistd` infrastructure:
# twistd -ny main.py
from twisted.application.service import Application
application = Application('The Web')
WebServer(port = 8070).setServiceParent(application)

if __name__=='__main__':
    from twisted.internet import reactor
    reactor.callLater(0, WebServer(port = 8070).startService)
    reactor.run()
