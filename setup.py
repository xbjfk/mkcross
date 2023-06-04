#!/usr/bin/env python

from setuptools import setup, Extension
import pathlib
import os
import subprocess

# I don't know what I'm doing. Have mercy


here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')

extension_llvm_config_args = {
	"include_dirs": ["includedir"],
	"library_dirs": ["libdir"],
	"extra_compile_args": ["cxxflags"],
	"extra_link_args": ["ldflags", "libs"] # Should be in libs but python only wants names which llvm-config doenst provide
}

llvm_config = os.getenv("LLVM_CONFIG", "llvm-config")

extension_args = {
	k : subprocess.run([llvm_config] + ['--' + x for x in v], check=True, capture_output=True, text=True).stdout.split()
	for k, v in extension_llvm_config_args.items()
}

extension_args["extra_compile_args"] += ["-fPIC"]

setup(
	name='mkcross',
	author_email='xbjfk.github@gmail.com',
	url='https://github.com/xbjfk/mkcross',
	license='MIT',
	version='0.0.1',
	description="easily cross compile without compiling GCC",
	long_description_content_type="text/markdown",
	long_description=long_description,
	packages=['mkcross', 'mkcross.targets', 'mkcross.helper'],
	ext_modules = [Extension(name="llvmtarget", sources=["mkcross/llvmtarget.cpp"], **extension_args)],
	keywords='clang llvm cross-compile',
	install_requires=[
		  'libarchive-c',
		  'requests',
		  'tqdm'
	],
	entry_points={
		'console_scripts': [
			'mkcross=mkcross.cli:main',
		],
	}

)
