import os

from jinja2.bccache import BytecodeCache
from jinja2.loaders import DictLoader

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
