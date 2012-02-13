import sys
import os
from os import path


def newFileName(directory):
    try:
        allfiles = os.listdir(directory)

    except OSError as e:
        print >> sys.stderr, "Error, no such directory %s" % (directory)
        raise(e)
    if len(allfiles) > 0:
        maxfile = max(allfiles)
        fname, ext = path.splitext(path.basename(maxfile))
        try:
            fnumber = int(fname)
            path.join(str(fnumber) + 

        except ValueError as e:
            
    else:
        return "0";


