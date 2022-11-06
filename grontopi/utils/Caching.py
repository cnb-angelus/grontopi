import cachetools
import datetime

CACHE_SIZE = 32 * 1024  # Number of Items to save
CACHE_LIFETIME = 300  # Number of seconds after which cache is invalid


class TimeLimitedCache:
    """
    This is a local cache to save small pieces of information that are
    likely to be asked in successive requests
    """
    def __init__(self,
                 ttl=CACHE_LIFETIME,
                 cache_size=CACHE_SIZE):
        self.cache = cachetools.TTLCache(maxsize=cache_size, ttl=ttl)
        self.lastread = datetime.datetime.now()
        # Cache won't last more than a day, no matter what
        # print("Started Cache ")

    def seconds_since_last_read(self):
        dt = datetime.datetime.now() - self.lastread
        return dt.seconds + 0.000001 * dt.microseconds

    def invalidate(self, delay=5):
        self.cache.clear()

    def __getitem__(self, item):
        return self.cache.get(item, None)

    def __setitem__(self, key, value):
        self.lastread = datetime.datetime.now()
        self.cache[key] = value

    def __len__(self):
        return len(self.cache)

    def __delitem__(self, key):
        self.cache.__delitem__(key)