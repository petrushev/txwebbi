from datetime import datetime, timedelta

from twisted.web.http import NOT_FOUND, OK, TEMPORARY_REDIRECT
from twisted.internet import reactor
from twisted.internet.task import deferLater

from txwebby import BaseController

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
        self.wait_seconds = int(self.request.args['num_seconds'][0])
        self.view['start'] = datetime.utcnow()
        d = deferLater(reactor, self.wait_seconds, self.step2)
        d.addErrback(self.server_error)
        # we don't call finish here!

    def step2(self):
        self.view.update({'path': self.request.path,
                          'req_delta': timedelta(seconds = self.wait_seconds),
                          'end': datetime.utcnow()})

        self.template = 'report.phtml'
        self.finish()

class PostReport(Report):
    pass

class Redirect(BaseController):
    def init(self):
        self.request.setResponseCode(TEMPORARY_REDIRECT)
        self.request.setHeader('Location', '/')
        self.finish()

class ErrorPage(BaseController):
    def init(self):
        raise Exception, 'Some error happened here.'
