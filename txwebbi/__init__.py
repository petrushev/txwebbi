from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.application.internet import TCPServer
from twisted.web.http import OK, Request, INTERNAL_SERVER_ERROR, HTTPChannel, HTTPFactory, NOT_FOUND
from twisted.python import log

from werkzeug.exceptions import NotFound as NotFoundException
from jinja2 import Environment

from txwebbi.jinja import MemoryTemplateCache, PreloadedDictLoader

class BaseController(object):

    def __init__(self, request, tpl_env, **kwargs):
        self.request = request
        self.tpl_env = tpl_env
        # it's set to False if we need to stop this request
        self._resume = True

        self.view = {}
        self.template = None

        # start processings
        init_task = deferLater(reactor, 0, self.init, **kwargs)
        init_task.addErrback(self.serverError)

    def init(**kwargs):
        """This is the main entry point for processing the request"""
        raise NotImplementedError

    def notifyDisconnect(self, reason):
        """Called on any lost connection"""
        pass

    def finish(self):
        """Should be called when we need to close up the request"""
        if self._resume is False: return

        if self.template is not None:
            tpl = self.tpl_env.get_template(self.template)
            content = tpl.render(**self.view)
            self.request.write(content.encode('utf-8'))

        self.request.finish()

    def redirect(self, location, permanent=False):
        """Sends a finished redirect response"""
        code = 301 if permanent else 302
        self.request.setResponseCode(code)
        self.request.setHeader('Location', location)
        self.finish()

    def serveStatic(self, path):
        """Should be called for delegation of serving static file at `path`"""
        try:
            fh = open(path, 'r')
        except (IOError, OSError):
            log.err('Error while reading static file @ ' + path)
            self.request.setResponseCode(NOT_FOUND)
            self.finish()

        else:
            deferLater(reactor, 0, self._serveChunk, fh, path)\
                .addErrback(self._errorServingChunk, fh, path)

    def _serveChunk(self, fh, path):
        data = fh.read(16384)
        len_data = len(data)
        if len_data > 0:
            self.request.write(data)
        if len(data) < 16384:
            fh.close()
            self.finish()

        else:
            deferLater(reactor, 0, self._serveChunk, fh, path)\
                .addErrback(self._errorServingChunk, fh, path)

    def _errorServingChunk(self, failure, fh, path):
        log.err('Error: possibly corrupted file @ %s\n    %s' \
                % (path, failure.getErrorMessage()))
        fh.close()
        self.finish()

    def serverError(self, reason):
        """Called when unhandled error in controller occurs
        can be reimplemented for other controllers"""
        log.err('Error: controller %s says: \n    %s' \
                % (self.__class__.__name__, reason.getErrorMessage()))

        if hasattr(self, 'error_template'):
            self.template = self.error_template

        self.request.setResponseCode(INTERNAL_SERVER_ERROR)
        self.finish()

def bootstrapCommonFrontHandler(url_map, template_path, NotFoundController):
    """Creates common front handler class"""

    tpl_env = Environment(loader = PreloadedDictLoader(template_path),
                          bytecode_cache = MemoryTemplateCache(),
                          auto_reload = False)

    # setup matcher for urls
    match = url_map.bind('').match

    class CommonFrontHandler(Request):

        def process(self):
            # set default headers
            self.setResponseCode(OK)
            self.setHeader('Content-Type', 'text/html; charset=UTF-8')

            # route to the proper controller class
            try:
                controllerClass, kwargs = match(self.path, method = self.method)
            except NotFoundException:
                controllerClass, kwargs = NotFoundController, {}

            # initialize controller
            self.controller = controllerClass(request = self, tpl_env = tpl_env, **kwargs)

            # disable controller for lost connections
            def connectionLost(reason):
                self.controller._resume = False
                self.controller.notifyDisconnect(reason)
            self.connectionLost = connectionLost

    return CommonFrontHandler

def bootstrapWebServer(FrontHandler):
    """Creates a WebServer service for a given FrontHandler protocol"""

    class FrontChannel(HTTPChannel):
        requestFactory = FrontHandler

    class FrontHttpFactory(HTTPFactory):
        protocol = FrontChannel

    frontFactory = FrontHttpFactory()

    class WebServer(TCPServer):
        def __init__(self, port = 80):
            TCPServer.__init__(self, port, frontFactory)

    return WebServer
