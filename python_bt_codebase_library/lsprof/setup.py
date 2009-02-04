try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from distutils.extension import Extension

setup(name        = "lsprof",
      author      = "Brett Rosen and Ted Czotter",
      py_modules  = ["cProfile", "pstats2", "lsprof"],
      package_dir = {'': 'Lib'},
      test_suite='nose.collector',
      ext_modules = [Extension(name = "_lsprof",
                               sources = ["Modules/_lsprof.c", "Modules/rotatingtree.c"])])
