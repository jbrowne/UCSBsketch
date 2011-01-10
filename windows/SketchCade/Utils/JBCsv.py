
class csv_reader(object):
    "Defines a basic CSV reader. Does not handle most corner cases (newlines, etc)"
    def __init__(self, filename, label_firstline = False):
        self.fp = open (filename)
        if label_firstline:
            labels = self.fp.readline().rstrip()
            self.labels = labels.split(',')
        else:
            self.labels = None
        self._dataDict = None
            
    def __iter__(self):
        return self
    
    def next(self):
        "Iterator for CSV reader. Returns None when the dictionary is done"
        values = self.fp.readline()
        if values == "":
            #raise StopIteration
            return None
        values = values.rstrip()
        values = values.split(',')
        if self.labels is None:# or len(self.labels) != len (values):
            return values
        else:
            try:
                retdict = {}
                for idx, label in enumerate(self.labels):

                    if idx not in range(len(values)) or values[idx] == "":
                        #return {}
                        val = None
                    else:
                        val = values[idx] #values[idx] = None
                    retdict[label] = val
            except Exception as e:
                for idx, label in enumerate(self.labels):
                    val = ""
                    if idx in range(len(values)):
                        val = values[idx]
                    print ("%s ::: %s" % (label, val))
                print e
                exit(1)
                    
            return retdict
    def getDataDict(self):
        if self._dataDict is None:
            self._dataDict = {}
            #try:
            for row in self:
                if row == None:
                    break
                if type(row) is dict:
                    for column, value in row.items():
                        try:
                            value = float(value)
                        except:
                            pass
                        val_list = self._dataDict.setdefault(column, [])
                        val_list.append(value)
                else:
                    for idx, value in enumerate(row):
                        try:
                            value = int(value)
                        except:
                            pass
                        val_list = self._dataDict.setdefault(idx, [])
                        val_list.append(value)
            #except:
            #    pass
        return dict(self._dataDict)
            

if __name__ == "__main__":
    for row in csv_reader('indata.csv', label_firstline = True):
        for label, value in row.items():
            print("%s :: %s" % (label, value))
        print("")
