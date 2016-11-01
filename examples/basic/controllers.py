from datetime import datetime, timedelta
from os.path import abspath, dirname
from os.path import join as path_join
from collections import deque

from twisted.web.http import NOT_FOUND, TEMPORARY_REDIRECT
from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.python import log

from txwebbi import BaseController

class NotFound(BaseController):
    def init(self):
        self.request.setResponseCode(NOT_FOUND)
        self.request.write('page not found. [404]')
        self.finish()

class Index(BaseController):
    def init(self):
        self.template = 'index.phtml'
        self.finish()

class Form(BaseController):
    def init(self):
        self.template = 'form.phtml'
        self.finish()

class Report(BaseController):
    def init(self):
        wait_seconds = self.request.args.get('num_seconds', (0,))[0]
        try:
            wait_seconds = float(wait_seconds)
        except ValueError:
            nf = NotFound(self.request, self.tpl_env)

        else:
            self.wait_seconds = wait_seconds

            self.view['start'] = datetime.utcnow()
            d = deferLater(reactor, self.wait_seconds, self.step2)
            d.addErrback(self.serverError)
            # we don't call finish here!

    def step2(self):
        self.view.update({'path': self.request.path,
                          'req_delta': timedelta(seconds = self.wait_seconds),
                          'end': datetime.utcnow()})

        self.template = 'report.phtml'
        self.finish()

class PostReport(Report):
    pass

class ParamReport(Report):
    def init(self, timeout):
        self.wait_seconds = timeout
        self.view['start'] = datetime.utcnow()
        d = deferLater(reactor, self.wait_seconds, self.step2)
        d.addErrback(self.serverError)

class Img(BaseController):
    def init(self):
        self.request.setHeader('Content-Type', 'image/jpg')
        static_path = abspath(dirname(__file__))
        static_path = path_join(static_path, 'static', 'test.jpg')
        self.serveStatic(static_path)

class Redirect(BaseController):
    def init(self):
        self.redirect('/')

class Servestream(BaseController):
    def init(self):
        self.request.setHeader('Content-Type', 'audio/mp3')
        #self.request.setHeader('Content-Type', 'video/mp4')

        self.stillReading = True
        self._data = deque()

        FrontHandler = self.request.__class__
        log.msg('listener added!')
        FrontHandler.listeners.add(self)

        def connectionLost(reason):
            self._data.clear()
            self.stillReading = False
            log.msg('listener removed!')
            FrontHandler.listeners.remove(self)

        self.request.connectionLost = connectionLost

        reactor.callLater(0, self.play)

    def streamFinished(self):
        self.stillReading = False

    def receiveUpdate(self, data):
        self._data.append(data)

    def play(self):
        if len(self._data) > 0:
            chunk = self._data.popleft()

            self.request.write(chunk)

            reactor.callLater(0, self.play)
            return

        if self.stillReading:
            reactor.callLater(0.2, self.play)
            return

        # _data is empty and finished reading
        self.finish()


class ErrorPage(BaseController):
    def init(self):
        raise Exception, 'Some error happened here.'
