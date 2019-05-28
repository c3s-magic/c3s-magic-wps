import os
import tempfile
import glob
import json
import sys

import logging

LOGGER = logging.getLogger("PYWPS")


def _dir_entry(path, name):
        result = dict()
        result['name'] = name
      
        contents = []

        dirs = os.listdir(path)
        for dir in dirs:
            subdir = os.path.join(path, dir)
            if (os.path.isdir(subdir)):
                contents.append(_dir_entry(subdir, dir))

        result['contents'] = contents

        return result

class DataFinder():
    def __init__(self, archive_base):
        self.archive_base = archive_base or '/data'
 
        self.data = _dir_entry(archive_base, 'root')

        print(self.data)

        print(json.dumps(self.data, indent=4), file=sys.stderr)


if __name__ == "__main__":
    DataFinder('/home/niels/Data/synda/cmip5/output1')
    