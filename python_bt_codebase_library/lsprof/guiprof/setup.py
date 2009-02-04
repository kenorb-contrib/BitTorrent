"""
Script for building the example.

Usage:
    python setup.py py2app
"""
from distutils.core import setup
import py2app

plist = dict(
    CFBundleDocumentTypes = [
        dict(
            CFBundleTypeExtensions=["pickle"],
            CFBundleTypeName="Stats Dump",
            CFBundleTypeRole="Viewer",
            NSDocumentClass="GPDoc",
        ),
    ]
)


setup(
    app=["GPDoc.py"],
    data_files=["MainMenu.nib", "GPDoc.nib"],
    options=dict(py2app=dict(plist=plist)),
)
