from __future__ import absolute_import

import errno

try:
    import cPickle as pickle
except ImportError:
    import pickle

import os
import tempfile
import time

import e3.log
from e3.fs import mkdir, rm
from e3.store.cache.backends.base import Cache, DEFAULT_TIMEOUT


class FileCache(Cache):

    cache_suffix = '.cache'

    def __init__(self, cache_configuration):
        super(FileCache, self).__init__(cache_configuration)
        self.cache_dir = cache_configuration['cache_dir']

    def clear(self):
        rm(os.path.join(self.cache_dir, '*.cache'))

    def delete(self, uid):
        rm(self.uid_to_file(uid))

    def _create_cache_dir(self):
        mkdir(self.cache_dir)

    def uid_to_file(self, uid):
        """Convert a resource uid to a cache file path.

        This backend assumes that the uid is a safe value for a file name.
        :param uid: the resource uid
        :type uid: str
        :rtype: str
        """
        return os.path.join(self.cache_dir, uid + self.cache_suffix)

    @staticmethod
    def _is_expired(fd):
        """Determine if an open cache file has expired.

        Automatically delete the file if it has passed its expiry time.
        """
        exp = pickle.load(fd)
        if exp is not None and exp < time.time():
            fd.close()
            print exp
            print '??? will deleted'
            #  rm(fd.name)
            return True
        return False

    def get(self, uid, default=None):
        cache_file = self.uid_to_file(uid)
        try:
            with open(cache_file, 'rb') as fd:
                if not self._is_expired(fd):
                    return pickle.load(fd)
        except IOError as err:
            if err.errno == errno.ENOENT:
                pass  # Cache file was removed after the exists check
        return default

    def set(self, uid, value, timeout=DEFAULT_TIMEOUT):
        # Make sure that teh cache dir exists
        self._create_cache_dir()
        dest_file = self.uid_to_file(uid)

        tmp_file = tempfile.NamedTemporaryFile(
            dir=self.cache_dir, delete=False)
        try:
            tmp_file.write(pickle.dumps(self.get_expiry_time(timeout),
                                        pickle.HIGHEST_PROTOCOL))
            tmp_file.write(pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
            tmp_file.close()

            os.rename(tmp_file.name, dest_file)

        except OSError as err:
            rm(tmp_file)
            e3.log.debug('error when setting %s in %s:\n%s',
                         uid, dest_file, err)