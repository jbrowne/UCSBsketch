import time
import functools

class Timed(object):
    def __init__(self, f):
        self.f = f
        self.name = f.__name__
    def __call__(self, *a, **kargs):
        #args = self.args + a
        start = time.time()
        retVal = self.f(self, *a, **kargs)
        print "TIMER: %s: %s ms" % (self.name, 1000 * (time.time() - start))
        return retVal
    def __get__(self, instance, instancetype):
        return functools.partial(self.__call__, instance)
