#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from conans import ConanFile, tools, CMake
from conanos.build import config_scheme


try:
    import conanos.conan.hacks.cmake
except:
    if os.environ.get('EMSCRIPTEN_VERSIONS'):
        raise Exception(
            'Please use pip install conanos to patch conan for emscripten binding !')


class LibpngConan(ConanFile):
    name = "libpng"
    version = "1.6.34"
    description = "libpng is the official PNG file format reference library."
    url = "http://github.com/bincrafters/conan-libpng"
    homepage = "http://www.libpng.org"
    license = "http://www.libpng.org/pub/png/src/libpng-LICENSE.txt"
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"

    source_subfolder = "source_subfolder"

    def is_emscripten(self):
        try:
            return self.settings.compiler == 'emcc'
        except:
            return False

    def requirements(self):
        self.requires.add("zlib/1.2.11@conanos/stable")

        config_scheme(self)


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.remove("fPIC")

    def configure(self):
        del self.settings.compiler.libcxx

        if self.is_emscripten():
            del self.settings.os
            del self.settings.arch
            self.options.remove("fPIC")
            self.options.remove("shared")
        
    def source(self):
        base_url = "https://sourceforge.net/projects/libpng/files/libpng16/"
        tools.get("%s/%s/libpng-%s.tar.gz" %
                  (base_url, self.version, self.version))
        #tools.get("%s/older-releases/%s/libpng-%s.tar.gz" % (base_url, self.version, self.version))
        os.rename("libpng-" + self.version, self.source_subfolder)
        os.rename(os.path.join(self.source_subfolder, "CMakeLists.txt"),
                  os.path.join(self.source_subfolder, "CMakeListsOriginal.txt"))
        shutil.copy("CMakeLists.txt",
                    os.path.join(self.source_subfolder, "CMakeLists.txt"))

    def build(self):
        if not self.is_emscripten() and self.settings.os == "Windows" and self.settings.compiler == "gcc":
            tools.replace_in_file("%s/CMakeListsOriginal.txt" % self.source_subfolder,
                                  'COMMAND "${CMAKE_COMMAND}" -E copy_if_different $<TARGET_LINKER_FILE_NAME:${S_TARGET}> $<TARGET_LINKER_FILE_DIR:${S_TARGET}>/${DEST_FILE}',
                                  'COMMAND "${CMAKE_COMMAND}" -E copy_if_different $<TARGET_LINKER_FILE_DIR:${S_TARGET}>/$<TARGET_LINKER_FILE_NAME:${S_TARGET}> $<TARGET_LINKER_FILE_DIR:${S_TARGET}>/${DEST_FILE}')
        # do not use _static suffix on VS
        if not self.is_emscripten() and self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            tools.replace_in_file("%s/CMakeListsOriginal.txt" % self.source_subfolder,
                                  'OUTPUT_NAME "${PNG_LIB_NAME}_static',
                                  'OUTPUT_NAME "${PNG_LIB_NAME}')

        if self.settings.build_type == 'Debug':
            tools.replace_in_file(os.path.join(self.source_subfolder, 'libpng.pc.in'),
                                  '-lpng@PNGLIB_MAJOR@@PNGLIB_MINOR@',
                                  '-lpng@PNGLIB_MAJOR@@PNGLIB_MINOR@d')

        if not self.is_emscripten() and 'arm' in self.settings.arch and self.settings.os == "Linux":
            tools.replace_in_file(os.path.join(self.source_subfolder, 'CMakeListsOriginal.txt'),
                                  'PATHS /usr/lib /usr/local/lib',
                                  'PATHS /usr/lib /usr/local/lib /usr/arm-linux-gnueabihf/lib /usr/arm-linux-gnueabi/lib ')

        if self.is_emscripten():
            tools.replace_in_file(os.path.join(self.source_subfolder, 'CMakeListsOriginal.txt'),
                                  'symbol_prefix()',
                                  '#symbol_prefix()')

            tools.replace_in_file(os.path.join(self.source_subfolder, 'CMakeListsOriginal.txt'),
                                  'if(NOT M_LIBRARY)',
                                  'set(M_LIBRARY "")\n  if(NOT M_LIBRARY)')

        cmake = CMake(self)

        cmake.definitions['CMAKE_INSTALL_LIBDIR'] = 'lib'
        cmake.definitions['CMAKE_INSTALL_BINDIR'] = 'bin'
        cmake.definitions['CMAKE_INSTALL_INCLUDEDIR'] = 'include'

        cmake.definitions["PNG_TESTS"] = "OFF"
        if self.is_emscripten():
            cmake.definitions["PNG_SHARED"] = "ON"
            cmake.definitions["PNG_STATIC"] = "OFF"
        else:
            cmake.definitions["PNG_SHARED"] = self.options.shared
            cmake.definitions["PNG_STATIC"] = not self.options.shared
        cmake.definitions["PNG_DEBUG"] = "OFF" if self.settings.build_type == "Release" else "ON"
        cmake.configure(source_folder=self.source_subfolder)
        cmake.build()
        cmake.install()

    def package(self):
        self.copy("LICENSE", src=self.source_subfolder,
                  dst="licenses", ignore_case=True, keep_path=False)
        shutil.rmtree(os.path.join(self.package_folder,
                                   'share', 'man'), ignore_errors=True)
        if not self.is_emscripten() and self.settings.os == "Windows":
            for s, r in {"@prefix@" : self.package_folder,
                         "@exec_prefix@" : "${prefix}",
                         "@libdir@" : "${prefix}/lib",
                         "@includedir@" : "${prefix}/include",
                         "@PNGLIB_MAJOR@" : self.version.split(".")[0],
                         "@PNGLIB_MINOR@" : self.version.split(".")[1],
                         "@PNGLIB_VERSION@" : self.version,
                         "@LIBS@" : ""}.items():
                tools.replace_in_file(os.path.join(self.source_folder, self.source_subfolder, 'libpng.pc.in'),s,r)
                tools.mkdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
                shutil.copy2(os.path.join(self.source_folder, self.source_subfolder, 'libpng.pc.in'),
                             os.path.join(self.package_folder, "lib", "pkgconfig", 'libpng.pc'))

    def package_info(self):
        if self.is_emscripten():
            self.cpp_info.libs = [
                "png16"] if self.settings.build_type == "Release" else ["png16d"]
            return

        if self.settings.os == "Windows":
            if self.settings.compiler == "gcc":
                self.cpp_info.libs = ["png"]
            else:
                self.cpp_info.libs = ['libpng16']
        else:
            self.cpp_info.libs = ["png16"]
            if self.settings.os == "Linux":
                self.cpp_info.libs.append("m")
        # use 'd' suffix everywhere except mingw
        if self.settings.build_type == "Debug" and not (self.settings.os == "Windows" and self.settings.compiler == "gcc"):
            self.cpp_info.libs[0] += "d"
