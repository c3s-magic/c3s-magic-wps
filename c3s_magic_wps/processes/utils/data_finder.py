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

        if len(contents) > 0:
            result['contents'] = contents

        return result

class DataFinder():
    def __init__(self, archive_base):
        self.archive_base = archive_base or '/data'
 
        self.data = _dir_entry(archive_base, 'root')

        print(self.data)

        print(json.dumps(self.data, indent=2), file=sys.stderr)


if __name__ == "__main__":
    DataFinder(sys.argv[1])
    