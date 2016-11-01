from os.path import join as pathjoin
from os.path import abspath, dirname


from werkzeug.routing import Rule, Map
from twisted.internet import reactor

from txwebbi import bootstrapWebServer, bootstrapCommonFrontHandler

import controllers

template_path = pathjoin(dirname(__file__), 'templates/')

url_map = Map([
    Rule('/', endpoint = controllers.Index),
    Rule('/form', endpoint = controllers.Form),
    Rule('/report', endpoint = controllers.Report, methods=['GET']),
    Rule('/report', endpoint = controllers.PostReport, methods=['POST']),
    Rule('/report/<int:timeout>', endpoint = controllers.ParamReport, methods=['GET']),
    Rule('/img', endpoint = controllers.Img, methods=['GET']),
    Rule('/redirect', endpoint = controllers.Redirect),
    Rule('/error', endpoint = controllers.ErrorPage),
    Rule('/stream', endpoint = controllers.Servestream)
])

FrontHandler = bootstrapCommonFrontHandler(url_map, template_path, controllers.NotFound)
FrontHandler.listeners = set()

def playVideo():
    static_path = abspath(dirname(__file__))
    static_path = pathjoin(static_path, 'static', 'test.mp3')

    fh = open(static_path, 'rb')

    def loop(buffer_kb=22):
        buffer_ = buffer_kb * 1024
        data = fh.read(buffer_)

        print 'stream read, listeners: %d' % len(FrontHandler.listeners)

        if len(data) == 0:
            fh.close()
            for listener in FrontHandler.listeners:
                listener.streamFinished()
            return

        for listener in FrontHandler.listeners:
            listener.receiveUpdate(data)

        reactor.callLater(1, loop, buffer_kb)

    reactor.callLater(0, loop)

reactor.callLater(0, playVideo)

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
