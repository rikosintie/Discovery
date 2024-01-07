#!/usr/bin/env python

"""
Creates a file in the same directory named offline.manifest,
or if that file already exists, replaces its contents with project files.
To ignore files of a particular type add their file extension to the ignore list.
"""

import os

manifest = "offline.manifest"
ignore = [".manifest", ".py", ".pyc", ".rb", ".sample", ".sass", ".sassc", ".scssc"]

file = open(manifest, "w")
file.write("CACHE MANIFEST\n")

for root, dirs, files in os.walk("./"):
    for name in files:
        filename = os.path.join(root, name)
        # Files like .DS_Store and .git will not have a file extension. To exclude them, first check if there is a file extension, and then if the file extension is in the list of file types to ignore.
        if (
            os.path.splitext(filename)[1] != ""
            and os.path.splitext(filename)[1] not in ignore
        ):
            file.write("%s\n" % filename)

file.close()
