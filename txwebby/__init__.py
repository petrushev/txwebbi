import os

from jinja2 import Environment
from jinja2.bccache import BytecodeCache
from jinja2.loaders import DictLoader
from werkzeug.exceptions import NotFound

from twisted.internet import reactor
from twisted.application.internet import TCPServer
from twisted.web import http

class BaseController(object):

    def __init__(self, request, tpl_env, **kwargs):
        self.request = request
        self.tpl_env = tpl_env
        # it's set to False if we need to stop this request
        self._resume = True

        self.view = {}
        self.template = None

        self.init(**kwargs)

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

    def callLater(self, seconds, fc, *args, **kwargs):
        reactor.callLater(seconds, fc, *args, **kwargs)

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

def bootstrapCommonFrontHandler(url_map, template_path, NotFoundController):
    """Creates common front handler class"""

    tpl_env = Environment(loader = PreloadedDictLoader(template_path),
                          bytecode_cache = MemoryTemplateCache(),
                          auto_reload = False)

    url_map_bind = url_map.bind

    class CommonFrontHandler(http.Request):

        def process(self):
            # set default headers
            self.setResponseCode(http.OK)
            self.setHeader('Content-Type', 'text/html; charset=UTF-8')

            # setup matcher for urls
            matcher = url_map_bind('', default_method=self.method)

            # route to the proper controller class
            try:
                controllerClass, kwargs = matcher.match(self.path)
            except NotFound:
                controllerClass, kwargs = NotFoundController, {}

            # init controller
            controller = controllerClass(request = self, tpl_env = tpl_env, **kwargs)

            # disable controller for lost connections
            def connectionLost(reason):
                controller._resume = False
                controller.notifyDisconnect(reason)
            self.connectionLost = connectionLost

    return CommonFrontHandler

def bootstrapWebServer(FrontHandler):

    class FrontChannel(http.HTTPChannel):
        requestFactory = FrontHandler

    class FrontHttpFactory(http.HTTPFactory):
        protocol = FrontChannel

    frontFactory = FrontHttpFactory()

    class WebServer(TCPServer):
        def __init__(self, port = 80):
            TCPServer.__init__(self, port, frontFactory)

    return WebServer
