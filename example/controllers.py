from datetime import datetime

from twisted.web.http import NOT_FOUND, OK, TEMPORARY_REDIRECT
from twisted.internet import reactor

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
        self.callLater(self.wait_seconds, self.step2)
        # we don't call finish here!

    def step2(self):
        self.view.update({'path': self.request.path,
                          'seconds': self.wait_seconds,
                          'end': datetime.utcnow()})

        self.template = 'report.phtml'
        self.finish()
