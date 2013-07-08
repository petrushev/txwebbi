import os

from jinja2 import Environment
from jinja2.bccache import BytecodeCache
from jinja2.loaders import DictLoader
from werkzeug.exceptions import NotFound

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.application.internet import TCPServer
from twisted.web.http import OK, Request, INTERNAL_SERVER_ERROR, HTTPChannel, HTTPFactory, NOT_FOUND
from twisted.python import log

class BaseController(object):

    def __init__(self, request, tpl_env, **kwargs):
        self.request = request
        self.tpl_env = tpl_env
        # it's set to False if we need to stop this request
        self._resume = True

        self.view = {}
        self.template = None

        # start processing
        init_task = deferLater(reactor, 0, self.init, **kwargs)
        init_task.addErrback(self.server_error)

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

    def serveStatic(self, path):
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
        data = fh.read(2048)
        self.request.write(data)
        if len(data) < 2048:
            fh.close()
            self.finish()
        else:
            deferLater(reactor, 1, self._serveChunk, fh, path)\
                .addErrback(self._errorServingChunk, fh, path)

    def _errorServingChunk(self, failure, fh, path):
        log.err('Error: possibly corrupted file @ ' + path + '\n    failure: ' + failure.getErrorMessage())
        self.finish()

    def server_error(self, reason):
        log.err('Error: controller %s says:' % self.__class__.__name__)
        log.err('    ' + reason.getErrorMessage())
        if hasattr(self, 'error_template'):
            self.template = self.error_template
        self.request.setResponseCode(INTERNAL_SERVER_ERROR)
        self.finish()

class MemoryTemplateCache(BytecodeCache):
    """Caches parsed jinja2 templates in memory"""

    def __init__(self):
        self._cache = {}
        BytecodeCache.__init__(self)

    def load_bytecode(self, bucket):
        code = self._cache.get(bucket.key, None)
        if code is not None:
            # loaded from cache
            bucket.bytecode_from_string(code)

    def dump_bytecode(self, bucket):
        self._cache[bucket.key] = bucket.bytecode_to_string()


class PreloadedDictLoader(DictLoader):
    """Jinja2 template loader of Dict type,
       loads all templates in memory at init"""

    def __init__(self, template_path):
        fullpaths = (os.path.join(path, fname)
                     for path, _, fnames in os.walk(template_path)
                     for fname in fnames)
        mapper = dict((fullpath.replace(template_path,''),
                       open(fullpath, 'r').read())
                      for fullpath in fullpaths)
        DictLoader.__init__(self, mapper)

class WebbiRequest(Request):

    def __init__(self, channel, queued):
        Request.__init__(self, channel, queued)
        self._channel = channel

    @property
    def channel(self):
        return self._channel

def bootstrapCommonFrontHandler(url_map, template_path, NotFoundController):
    """Creates common front handler class"""

    tpl_env = Environment(loader = PreloadedDictLoader(template_path),
                          bytecode_cache = MemoryTemplateCache(),
                          auto_reload = False)

    # setup matcher for urls
    match = url_map.bind('').match

    class CommonFrontHandler(WebbiRequest):

        def process(self):
            # set default headers
            self.setResponseCode(OK)
            self.setHeader('Content-Type', 'text/html; charset=UTF-8')

            # route to the proper controller class
            try:
                controllerClass, kwargs = match(self.path, method = self.method)
            except NotFound:
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