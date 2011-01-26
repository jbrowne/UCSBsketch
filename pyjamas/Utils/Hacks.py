"""
Utils/Hacks.py

This could be a good place to put assorted hacks that are needed on certain platforms.

"""
from Utils import Logger
logger = Logger.getLogger("Hacks", Logger.DEBUG)


def type(obj):
   """ 
   Returns a string of the name of the object passed in.
   Good if 'type' is undefined (*ahem* pyjamas).
   """
   logger.debug( getattr(obj, "__class__") )
   return obj.__name__
