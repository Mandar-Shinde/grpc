# Copyright 2015-2016, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""A setup module for the GRPC Python package."""

import os
import os.path
import shutil
import sys

from distutils import core as _core
from distutils import extension as _extension
import setuptools
from setuptools.command import egg_info

# Redirect the manifest template from MANIFEST.in to PYTHON-MANIFEST.in.
egg_info.manifest_maker.template = 'PYTHON-MANIFEST.in'

PYTHON_STEM = './src/python/grpcio'
CORE_INCLUDE = ('./include', '.',)
BORINGSSL_INCLUDE = ('./third_party/boringssl/include',)
ZLIB_INCLUDE = ('./third_party/zlib',)

# Ensure we're in the proper directory whether or not we're being used by pip.
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(PYTHON_STEM))

# Break import-style to ensure we can actually find our in-repo dependencies.
import commands
import grpc_core_dependencies

LICENSE = '3-clause BSD'

# Environment variable to determine whether or not the Cython extension should
# *use* Cython or use the generated C files. Note that this requires the C files
# to have been generated by building first *with* Cython support.
BUILD_WITH_CYTHON = os.environ.get('GRPC_PYTHON_BUILD_WITH_CYTHON', False)

# Environment variable to determine whether or not to enable coverage analysis
# in Cython modules.
ENABLE_CYTHON_TRACING = os.environ.get(
    'GRPC_PYTHON_ENABLE_CYTHON_TRACING', False)

# Environment variable to determine whether or not to include the test files in
# the installation.
INSTALL_TESTS = os.environ.get('GRPC_PYTHON_INSTALL_TESTS', False)

CYTHON_EXTENSION_PACKAGE_NAMES = ()

CYTHON_EXTENSION_MODULE_NAMES = ('grpc._cython.cygrpc',)

CYTHON_HELPER_C_FILES = (
    os.path.join(PYTHON_STEM, 'grpc/_cython/loader.c'),
    os.path.join(PYTHON_STEM, 'grpc/_cython/imports.generated.c'),
)

CORE_C_FILES = ()
if not "win32" in sys.platform:
  CORE_C_FILES += tuple(grpc_core_dependencies.CORE_SOURCE_FILES)

EXTENSION_INCLUDE_DIRECTORIES = (
    (PYTHON_STEM,) + CORE_INCLUDE + BORINGSSL_INCLUDE + ZLIB_INCLUDE)

EXTENSION_LIBRARIES = ()
if "linux" in sys.platform:
  EXTENSION_LIBRARIES += ('rt',)
if not "win32" in sys.platform:
  EXTENSION_LIBRARIES += ('m',)

DEFINE_MACROS = (('OPENSSL_NO_ASM', 1), ('_WIN32_WINNT', 0x600))

CFLAGS = ()
LDFLAGS = ()
if "linux" in sys.platform:
  LDFLAGS += ('-Wl,-wrap,memcpy',)
if "linux" in sys.platform or "darwin" in sys.platform:
  CFLAGS += ('-fvisibility=hidden',)
  DEFINE_MACROS += (('PyMODINIT_FUNC', '__attribute__((visibility ("default"))) void'),)


def cython_extensions(package_names, module_names, extra_sources, include_dirs,
                      libraries, define_macros, build_with_cython=False):
  if ENABLE_CYTHON_TRACING:
    define_macros = define_macros + [('CYTHON_TRACE_NOGIL', 1)]
  file_extension = 'pyx' if build_with_cython else 'c'
  module_files = [os.path.join(PYTHON_STEM,
                               name.replace('.', '/') + '.' + file_extension)
                  for name in module_names]
  extensions = [
      _extension.Extension(
          name=module_name,
          sources=[module_file] + extra_sources,
          include_dirs=include_dirs, libraries=libraries,
          define_macros=define_macros,
          extra_compile_args=list(CFLAGS),
          extra_link_args=list(LDFLAGS),
      ) for (module_name, module_file) in zip(module_names, module_files)
  ]
  if build_with_cython:
    import Cython.Build
    return Cython.Build.cythonize(
        extensions,
        include_path=include_dirs,
        compiler_directives={'linetrace': bool(ENABLE_CYTHON_TRACING)})
  else:
    return extensions

CYTHON_EXTENSION_MODULES = cython_extensions(
    list(CYTHON_EXTENSION_PACKAGE_NAMES), list(CYTHON_EXTENSION_MODULE_NAMES),
    list(CYTHON_HELPER_C_FILES) + list(CORE_C_FILES),
    list(EXTENSION_INCLUDE_DIRECTORIES), list(EXTENSION_LIBRARIES),
    list(DEFINE_MACROS), bool(BUILD_WITH_CYTHON))

PACKAGE_DIRECTORIES = {
    '': PYTHON_STEM,
}

INSTALL_REQUIRES = (
    'six>=1.10',
    'enum34>=1.0.4',
    'futures>=2.2.0',
    # TODO(atash): eventually split the grpcio package into a metapackage
    # depending on protobuf and the runtime component (independent of protobuf)
    'protobuf>=3.0.0a3',
)

SETUP_REQUIRES = (
    'sphinx>=1.3',
) + INSTALL_REQUIRES

COMMAND_CLASS = {
    'install': commands.Install,
    'doc': commands.SphinxDocumentation,
    'build_proto_modules': commands.BuildProtoModules,
    'build_project_metadata': commands.BuildProjectMetadata,
    'build_py': commands.BuildPy,
    'build_ext': commands.BuildExt,
    'gather': commands.Gather,
    'run_interop': commands.RunInterop,
    'bdist_egg_grpc_custom': commands.BdistEggCustomName,
}

# Ensure that package data is copied over before any commands have been run:
credentials_dir = os.path.join(PYTHON_STEM, 'grpc/_adapter/credentials')
try:
  os.mkdir(credentials_dir)
except OSError:
  pass
shutil.copyfile('etc/roots.pem', os.path.join(credentials_dir, 'roots.pem'))

TEST_PACKAGE_DATA = {
    'tests.interop': [
        'credentials/ca.pem',
        'credentials/server1.key',
        'credentials/server1.pem',
    ],
    'tests.protoc_plugin': [
        'protoc_plugin_test.proto',
    ],
    'tests.unit': [
        'credentials/ca.pem',
        'credentials/server1.key',
        'credentials/server1.pem',
    ],
}

TESTS_REQUIRE = (
    'oauth2client>=1.4.7',
    'protobuf>=3.0.0a3',
    'coverage>=4.0',
) + INSTALL_REQUIRES

TEST_SUITE = 'tests'
TEST_LOADER = 'tests:Loader'
TEST_RUNNER = 'tests:Runner'

PACKAGE_DATA = {
    'grpc._adapter': [
        'credentials/roots.pem'
    ],
    'grpc._cython': [
        '_windows/grpc_c.32.python',
        '_windows/grpc_c.64.python',
    ],
}
if INSTALL_TESTS:
  PACKAGE_DATA = dict(PACKAGE_DATA, **TEST_PACKAGE_DATA)
  PACKAGES = setuptools.find_packages(PYTHON_STEM)
else:
  PACKAGES = setuptools.find_packages(
      PYTHON_STEM, exclude=['tests', 'tests.*'])

setuptools.setup(
    name='grpcio',
    version='0.12.0b8',
    license=LICENSE,
    ext_modules=CYTHON_EXTENSION_MODULES,
    packages=list(PACKAGES),
    package_dir=PACKAGE_DIRECTORIES,
    package_data=PACKAGE_DATA,
    install_requires=INSTALL_REQUIRES,
    setup_requires=SETUP_REQUIRES,
    cmdclass=COMMAND_CLASS,
    tests_require=TESTS_REQUIRE,
    test_suite=TEST_SUITE,
    test_loader=TEST_LOADER,
    test_runner=TEST_RUNNER,
)
