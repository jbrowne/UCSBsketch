DEBUG = 0
WARN = 1
ERROR = 2
FATAL = 3
class _LoggerStub(object):
   ALL_LOGGERS = []
   def __init__(self, tag = "", level = FATAL):
      self.tag = tag
      self.level = level
      _LoggerStub.ALL_LOGGERS.append(self)
   
   def debug(self, msg):
      if self.level <= DEBUG:
         print "%s: %s" % (self.tag, msg)
   def warn(self, msg):
      if self.level <= WARN:
         print "%s: %s" % (self.tag, msg)
   def error(self, msg):
      if self.level <= ERROR:
         print "%s: %s" % (self.tag, msg)
   def fatal(self, msg):
      if self.level <= FATAL:
         print "%s: %s" % (self.tag, msg)

   def setLevel (self, level):
      self.level = level

# this gets a new logger for the module
# changes to the logging format should be made
# here so they are uniform across the modules
def getLogger( name, level ):
   return _LoggerStub(tag = name, level = level)

# this is the default level during doctest mode
def setDoctest( logger ):
    # set all of the loggers to the doctest level
    for l in _LoggerStub.ALL_LOGGERS:
        l.setLevel(WARN)

