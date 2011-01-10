import logging

logging.basicConfig(level=logging.WARN)

DEBUG = logging.DEBUG
WARN = logging.WARN
ERROR = logging.ERROR
FATAL = logging.FATAL

try:
    _is_init == None
except NameError:
    _isdoctest=False
    _doctest_level=logging.WARN
    _all_loggers=[]
    _is_init = None

# this gets a new logger for the module
# changes to the logging format should be made
# here so they are uniform across the modules
def getLogger( name, level ):
    logger = logging.getLogger(name)
    _all_loggers.append(logger)
    if( _isdoctest ):
        logger.setLevel(_doctest_level)
    else:
        logger.setLevel(level)
    return logger

# this is the default level during doctest mode
def setDoctest( logger ):
    _isdoctest = True
    # set all of the loggers to the doctest level
    for l in _all_loggers:
        l.setLevel(_doctest_level)
