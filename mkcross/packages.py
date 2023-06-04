import os
import shutil
from distutils.dir_util import copy_tree
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List
from mkcross.helper.flags import join_map_flags

import mkcross.helper.latest_version as latest_ver

import libarchive
import requests
from tqdm import tqdm

from mkcross import cfg
import llvmtarget
from mkcross.targets.targetmeta import TargetMeta


# TODO verify/skip download
class Downloader:
	url: str
	temppath: Path
	path: Path
	filename: str

	def __init__(self, url: str, filename: str):
		self.url = url
		self.path = cfg.dlpath / filename
		self.temppath = Path(str(self.path) + ".__download__")
		self.filename = filename

	# TODO resume download
	def download(self):
		# TODO force redownloads option
		# TODO tqdm, maybe global array of current progress operations
		if not self.path.exists():
			print("Downloading " + self.url)
			resume = self.temppath.exists()
			headers = {"Range": "bytes=" + str(self.temppath.stat().st_size) + "-"} if resume else {}
			r = requests.get(self.url, headers=headers, allow_redirects=True, stream=True)
			r.raise_for_status()

			if resume:
				print("Resuming download of " + self.url)
				try:
					r.headers["accept-ranges"] # Throw if not exists
					resume_works = True
				except KeyError:
					resume_works = False

			file_size = int(r.headers.get("Content-Length", 0))

			mode = "ab" if resume and resume_works else "wb"

			with open(self.temppath, mode) as handle:
				for data in tqdm(r.iter_content(chunk_size=8192), total=__import__("math").ceil(file_size/8192), desc="Download " + self.filename):
					handle.write(data)

			self.temppath.rename(self.path)
		else:
			print("Already downloaded " + self.url)


class PackageFile:
	url: str
	filename: str
	path: Path
	# None for non-downloadable files eg macos sdk
	downloader: Downloader
	missing_message: str

	def __init__(self, url: str, filename: str = None):
		self.url = url
		if filename is None:
			filename = url.split('/')[-1]
		self.path = cfg.dlpath / filename
		self.filename = filename
		if url is not None:
			self.downloader = Downloader(url, filename)


class PackageMeta(ABC):
	files: List[PackageFile]
	target: TargetMeta
	# dep_host_exe: List[str]
	# TODO dep checking based on class name, check in check method, each package prechecked deps and validity
	def __init__(self, target: TargetMeta, files: [PackageFile]):
		self.target = target

		self.files = files

	def download(self):
		for file in self.files.values():
			if file.downloader is not None:
				file.downloader.download()

	@staticmethod
	def get_latest_version(self):
		return NotImplemented

	def prepare(self):
		pass

	def build(self):
		pass

	@abstractmethod
	def install(self):
		return NotImplemented


class SourcePackage(PackageMeta):
	files: List[PackageFile]
	name: str
	ver: str
	srcdir: Path
	builddir: Path

	def __init__(self, target: TargetMeta, files: Dict[str, PackageFile], name: str, ver: str, srcdir: Path = None):
		# TODO substitute ver into url
		super().__init__(target, files)
		self.name = name
		self.ver = ver
		self.srcdir = Path(cfg.srcpath / (self.name + '-' + self.ver)) if srcdir is None else srcdir
		self.builddir = Path(cfg.buildpath / (target.llvmtarget.triplestr + '-' + self.name + '-' + self.ver))
		self.builddir.mkdir(parents=True, exist_ok=True)

	def prepare(self):
		# TODO threads
		# TODO move this logic somewhere else so same filenames are ok

		# https://bugs.python.org/issue40358
		src = Path(os.path.relpath(cfg.srcpath))
		for file in self.files.values():
			extractcheckpath = cfg.srcpath / ("." + file.filename + ".__extracted__")
			if not extractcheckpath.exists():
				with tqdm(total=file.path.stat().st_size, desc="Extract " + file.filename) as bar, \
					libarchive.file_reader(str(file.path)) as archive:
					for entry in archive:
						# TODO read extractdir for packages that are stupid
						entry.pathname = str(src / entry.pathname)
						libarchive.extract.extract_entries([entry])
						bar.update(archive.bytes_read - bar.n)
					extractcheckpath.touch()
			else:
				print("Already extracted " + file.filename)

	def configure(self):
		pass

	@abstractmethod
	def build(self):
		return NotImplemented

	@abstractmethod
	def install(self):
		return NotImplemented

	def make(self, *targets, dir: Path = None, prog: str = "make", check = True):
		if dir is None:
			dir = self.builddir
		subprocess.run([prog] + cfg.makeopts + ["-C", str(dir), *targets], check=check),


class Linux(SourcePackage):
	headers_only: bool

	@staticmethod
	def get_latest_version():
		r = requests.get("https://www.kernel.org/releases.json")
		r.raise_for_status()
		return r.json()["latest_stable"]["version"]

	# alpha, h8300, ia64, microblaze, nds32, nios2, openrisc, parisc, sh, are not implemented or were removed from LLVM
	@staticmethod
	def arch_for_llvm(target: llvmtarget.LLVMTarget):
		arch = target.arch
		if target.is_aarch64:
			return "arm64"
		elif target.is_mips:
			return "mips"
		elif target.is_ppc:
			return "powerpc"
		elif target.is_riscv:
			return "riscv"
		elif target.is_systemz:
			return "s390"
		elif target.is_x86:
			return "x86"
		elif target.is_arm or target.is_thumb:
			return "arm"
		elif target.is_sparc:
			return "sparc"
		elif arch in ['arc', 'csky', 'hexagon', 'm68k']:
			return arch
		else:
			raise ValueError(f"Target {arch.name} is not supported by the linux kernel!")

	def __init__(self, target: TargetMeta, ver: str, headers_only=False):
		if ver is None:
			ver = self.get_latest_version()

		self.headers_only = headers_only
		files = {
			f"linux-{ver}.tar.xz": PackageFile(f"https://cdn.kernel.org/pub/linux/kernel/v{ver.split('.')[0]}.x/linux-{ver}.tar.xz"),
		}
		super().__init__(target, files, "linux", ver)

	def build(self):
		if not self.headers_only:
			pass
	
	def install(self):
		if self.headers_only:
			self.make("headers_install",
				"ARCH=" + Linux.arch_for_llvm(self.target.llvmtarget),
				"O=" + str(self.builddir),
				"INSTALL_HDR_PATH=" + str(self.target.sysroot.resolve()),
				dir=self.srcdir)
		#will only be not headers only if target specifies build kernel


class Musl(SourcePackage):
	headers_only: bool

	def __init__(self, target: TargetMeta, ver: str = None, headers_only=False):
		self.headers_only = headers_only
		url = f"https://musl.libc.org/releases/musl-{ver}.tar.gz"
		files = {
			f"musl-{ver}.tar.gz": PackageFile(url),
		}
		super().__init__(target, files, "musl", ver)

	@staticmethod
	def get_latest_version():
		return latest_ver.git("https://git.musl-libc.org/git/musl")[1:]

	def configure(self):
		# TODO default buildpath and srcpath in thing
		# TODO env to target or sourcepackage
		env = {
			# Put target and stuff in CC because try_ldflag doesn't respect CFLAGS and will try add lgcc_eh because it exists on the host
			"CC": shutil.which("clang") + " -target " + self.target.llvmtarget.triplestr + " --sysroot " + str(self.target.sysroot.resolve()) + " -resource-dir " + str(self.target.sysroot.resolve() / "lib/clang"),
			"AR": shutil.which("llvm-ar"),
			"RANLIB": shutil.which("llvm-ranlib"),
			"CFLAGS": join_map_flags(self.target.cflags, self.target.sysroot)
		}
		subprocess.run([str((self.srcdir / "configure").resolve()), "--disable-gcc-wrapper", "--target=" + self.target.llvmtarget.triplestr, "--prefix=/"], env=env, cwd=self.builddir, check=True)

	def build(self):
		self.make("obj/include/bits/alltypes.h")
		if not self.headers_only:
			self.make()

	def install(self):
		install_target = "install-headers" if self.headers_only else "install"
		self.make("DESTDIR=" + str(self.target.sysroot.resolve()), install_target)

		#will only be not headers only if target specifies build kernel


class CMakePackage(SourcePackage):
	def __init__(self, target: TargetMeta, files: Dict[str, PackageFile], name: str, ver: str, cmake_opts={}, srcdir: Path = None):
		super().__init__(target, files, name, ver, srcdir)
		self.cmake_opts = cmake_opts

	def configure(self):
		user_args = [f"-D{k}={v}" for k, v in self.cmake_opts.items()]

		args = [
			"cmake", "-GNinja",
			"-S" + str(self.srcdir),
			"-B" + str(self.builddir),
			"-DCMAKE_TOOLCHAIN_FILE=" + str(self.target.cross_file_cmake),
			"-DCMAKE_INSTALL_PREFIX=/", # Some targets support /usr some don't, but all support /include (ie mingw and bare metal)
		]

		if self.target.llvmtarget.is_mingw:
			args += ["-DCMAKE_INSTALL_INCLUDEDIR=/include"]

		args += user_args
		print("[I] Running", shlex.join(args))
		subprocess.run(args, check=True)

	def build(self):
		subprocess.run(["ninja", "-C", str(self.builddir)], check=True)

	def install(self):
		subprocess.run(["ninja", "-C", str(self.builddir), "install"], env={"DESTDIR": str(self.target.sysroot.resolve())}, check=True),


class AutotoolsPackage(SourcePackage):
	def __init__(self, target: TargetMeta, files: Dict[str, PackageFile], name: str, ver: str, autoconf_opts=[], supports_outoftree=True, srcdir: Path = None, prefix: str = None):
		self.autoconf_opts = autoconf_opts
		self.supports_outoftree = supports_outoftree
		self.prefix = prefix or str()
		super().__init__(target, files, name, ver, srcdir)

	def configure(self, force_autoreconf=False):
		olddir = os.getcwd()

		configure_script = self.srcdir / "configure"
		if not configure_script.exists() or force_autoreconf:
			subprocess.run(['autoreconf', '--install', '--symlink', '--verbose'], check=True, cwd=self.srcdir)

		if self.supports_outoftree:
			workdir = self.builddir
		else:
			workdir = self.srcdir
			self.make("distclean", dir=self.srcdir, check=False)

		sysroot = self.target.sysroot

		configure_args = [
			str(configure_script),
			f'CC={shutil.which("clang")}',
			f'AS={shutil.which("clang")}',
			f'ASFLAGS={join_map_flags(self.target.cflags, sysroot)}',
			f'CXX={shutil.which("clang++")}',
			f'CFLAGS={join_map_flags(self.target.cflags, sysroot)}',
			f'CXXFLAGS={join_map_flags(self.target.cxxflags, sysroot)}',
			f'LDFLAGS={join_map_flags(self.target.ldflags, sysroot)}',
			f'AR={shutil.which("llvm-ar")}',
			f'RANLIB={shutil.which("llvm-ranlib")}',
			f'NM={shutil.which("llvm-nm")}',
			f'DLLTOOL={shutil.which("llvm-dlltool")}',
			f'--host={self.target.llvmtarget.arch + "-w64-mingw32" if self.target.llvmtarget.is_mingw else self.target.llvmtarget.triplestr}', # Normalized mingw is ARCH-unknown-windows-gnu
			f'--prefix={self.prefix}',
		] + self.autoconf_opts

		print("[I] Running", shlex.join(configure_args))

		subprocess.run(configure_args, cwd=workdir)

	def build(self):
		self.make(dir=self.builddir if self.supports_outoftree else self.srcdir)

	def install(self, destdir=None):
		destdir = str(destdir or self.target.sysroot.resolve())
		dir = self.builddir if self.supports_outoftree else self.srcdir
		self.make("DESTDIR=" + destdir, "install", dir=dir)




class MingwHeaders(AutotoolsPackage):
	def __init__(self, target: TargetMeta, ver: str):
		files = {
			f"mingw-w64-v{ver}.tar.bz2": PackageFile(f"https://versaweb.dl.sourceforge.net/project/mingw-w64/mingw-w64/mingw-w64-release/mingw-w64-v{ver}.tar.bz2")
		}
		srcdir = Path(cfg.srcpath / ("mingw-w64-v" + ver) / "mingw-w64-headers")
		# /include is the architecture agnostic include, /usr/include is not checked
		super().__init__(target, files, "mingw-headers", ver, supports_outoftree=False, srcdir=srcdir, prefix="/")


class Mingw(AutotoolsPackage):
	def __init__(self, target: TargetMeta, ver: str):
		files = {
			f"mingw-w64-v{ver}.tar.bz2": PackageFile(f"https://versaweb.dl.sourceforge.net/project/mingw-w64/mingw-w64/mingw-w64-release/mingw-w64-v{ver}.tar.bz2")
		}
		srcdir = Path(cfg.srcpath / ("mingw-w64-v" + ver))
		
		self.__mingw_libdir = {
			"i386": "lib32",
			"x86_64": "lib64",
			"arm": "libarm32",
			"aarch64": "libarm64"
		}[target.llvmtarget.arch]

		# Multilib not supported for Arm32/64.
		# See https://sourceforge.net/p/mingw-w64/feature-requests/107/

		opts = ["--disable-lib32", "--disable-lib64", "--disable-libarm32", "--disable-libarm64"]
		opts += [ "--enable-" + self.__mingw_libdir]

		super().__init__(target, files, "mingw", ver, autoconf_opts=opts, supports_outoftree=False, srcdir=srcdir)

	def install(self):
		# Manually install into the paths clang wants.
		super().install(destdir=self.builddir)

		
		copy_tree(str(self.builddir / self.__mingw_libdir), str(self.target.sysroot / "lib"))
		
		
		# Multilib:
		#arch = self.target.arch
		#is64 = arch in [ArchType.x86_64, ArchType.aarch64]
		#isarm = arch in [ArchType.arm, ArchType.aarch64]
		#supports_multilib = not isarm
        #
		#if is64:
		#	lib32 = "lib32"
		#	lib64 = "lib"
		#	
		#	arch32 = ArchType.arm if isarm else ArchType.i386
		#	arch64 = arch
		#else:
		#	lib32 = "lib"
		#	lib64 = "lib64"
        #
		#	arch32 = arch
		#	arch64 = ArchType.aarch64 if isarm else ArchType.x86_64
        #
        #
		## Only native is built when no multilib
		#if arch == arch32 or supports_multilib:
		#	copy_tree(self.builddir / lib32, self.target.sysroot / (arch32.name + "-w64-mingw32") / "lib")
        #
		#if arch == arch64 or supports_multilib:
		#	copy_tree(self.builddir / lib64, self.target.sysroot / (arch64.name + "-w64-mingw32") / "lib")

class PicoLibc(CMakePackage):
	@staticmethod
	def get_latest_version():
		return latest_ver.github("picolibc/picolibc")

	def __init__(self, target: TargetMeta, ver: str):
		files = {
			f"cppwinrt-{ver}.tar.gz": PackageFile(f"https://github.com/picolibc/picolibc/releases/download/{ver}/picolibc-{ver}.tar.xz"),
		}
		opts = {
			"CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY",
		}
		super().__init__(target, files, "picolibc", ver, opts)

	def install(self):
		super().install()
		# Create dummy libm
		# See: https://github.com/picolibc/picolibc/issues/462
		subprocess.run(["llvm-ar", "rcs", str(self.target.sysroot / "lib/libm.a")])

class CppWinRT(CMakePackage):
	def __init__(self, target: TargetMeta, ver: str):
		files = {
			f"cppwinrt-{ver}.tar.gz": PackageFile(f"https://github.com/microsoft/cppwinrt/archive/refs/tags/{ver}.tar.gz", filename=f"cppwinrt-{ver}.tar.gz"),
		}
		opts = {

		}
		super().__init__(target, files, "cppwinrt", ver, opts)



class CompilerRT(CMakePackage):
	def __init__(self, target: TargetMeta, ver: str):
		files = {
			f"llvmorg-{ver}.tar.gz": PackageFile(f"https://github.com/llvm/llvm-project/archive/refs/tags/llvmorg-{ver}.tar.gz"),
		}
		srcdir = Path(cfg.srcpath / ("llvm-project-llvmorg-" + ver) / "runtimes")
		opts = {
			"COMPILER_RT_INSTALL_PATH": "/lib/clang",
			"LLVM_BINARY_DIR": str(target.sysroot.resolve() / "usr" / "lib" / "llvm"),
			"LLVM_ENABLE_RUNTIMES": "compiler-rt",

			"COMPILER_RT_BUILD_BUILTINS": "ON",
			"COMPILER_RT_BUILD_CRT": "ON" if target.llvmtarget.is_linux else "OFF",
			"COMPILER_RT_DEFAULT_TARGET_ONLY": "ON",

			"LLVM_INCLUDE_TESTS": "OFF",
			"LLVM_ENABLE_LIBCXX": "ON",

			"CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY",

			"COMPILER_RT_BUILD_LIBFUZZER": "OFF",
			"COMPILER_RT_BUILD_MEMPROF": "OFF",
			"COMPILER_RT_BUILD_PROFILE": "OFF",
			"COMPILER_RT_BUILD_SANITIZERS": "OFF",
			"COMPILER_RT_BUILD_XRAY": "OFF",
			"COMPILER_RT_BUILD_ORC": "OFF",
		}

		if target.llvmtarget.is_baremetal:
			# LLVM uses this to test if linker script is available: 
			# https://github.com/llvm/llvm-project/blob/main/llvm/cmake/modules/HandleLLVMOptions.cmake#L135
			opts["UNIX"] = "1"

			opts["COMPILER_RT_BAREMETAL_BUILD"] = "1"
			opts["COMPILER_RT_OS_DIR"] = "baremetal" # CMake OS is generic, but clang searches in baremetal

		super().__init__(target, files, "compiler-rt", ver, opts, srcdir)


# mm_malloc.h, compiler intrinsics, etc
class ClangResourceHeaders(PackageMeta):
	def __init__(self, target: TargetMeta):
		super().__init__(target, [])

	def install(self):
		p = subprocess.run(['clang','-print-resource-dir'], capture_output=True, check=True, text=True)
		system_resources = Path(p.stdout[:-1])
		copy_tree(str(system_resources / "include"), str(self.target.sysroot / "lib/clang/include"))


class Libunwind(CMakePackage):
	def __init__(self, target: TargetMeta, ver: str):
		files = {
			f"llvmorg-{ver}.tar.gz": PackageFile(f"https://github.com/llvm/llvm-project/archive/refs/tags/llvmorg-{ver}.tar.gz"),
		}
		srcdir = Path(cfg.srcpath / ("llvm-project-llvmorg-" + ver) / "runtimes")
		opts = {
			"LLVM_ENABLE_RUNTIMES": "libunwind",
			"LIBUNWIND_INSTALL_HEADERS": "ON",
			"LLVM_INCLUDE_TESTS": "OFF",
			"LLVM_ENABLE_LIBCXX": "ON",
			"LIBUNWIND_USE_COMPILER_RT": "ON",
			# Libunwind will try add these but we do this now so the try compile will work
			"CMAKE_EXE_LINKER_FLAGS": join_map_flags(target.ldflags, target.sysroot) + ' --unwindlib=none -nostdlib++',
			# This makes it too optimistic, and it tries to link lgcc and lgcc_s.
			#"CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY",

			# alloca.h is included with stdlib.h only when __STRICT_ANSI__ is unset...
			"CMAKE_CXX_FLAGS": join_map_flags(target.cxxflags, target.sysroot) + ' -include alloca.h',
		}
		if target.llvmtarget.is_baremetal:
			# LLVM uses this to test if linker script is available: 
			# https://github.com/llvm/llvm-project/blob/main/llvm/cmake/modules/HandleLLVMOptions.cmake#L135
			opts["UNIX"] = "1"

			opts["LIBUNWIND_IS_BAREMETAL"] = "1"
			opts["LIBUNWIND_ENABLE_THREADS"] = "0" # no threads

		if target.llvmtarget.is_mingw or target.llvmtarget.is_baremetal:
			opts["LIBUNWIND_ENABLE_SHARED"] = "OFF"

		super().__init__(target, files, "llvm-libunwind", ver, opts, srcdir)



class LibCXX(CMakePackage):
	def __init__(self, target: TargetMeta, ver: str):
		files = {
			f"llvmorg-{ver}.tar.gz": PackageFile(f"https://github.com/llvm/llvm-project/archive/refs/tags/llvmorg-{ver}.tar.gz"),
		}
		srcdir = Path(cfg.srcpath / ("llvm-project-llvmorg-" + ver) / "runtimes")
		opts = {
			"LLVM_ENABLE_RUNTIMES": "libcxxabi;libcxx",
			"LLVM_INCLUDE_TESTS": "OFF",
			"LLVM_ENABLE_LIBCXX": "ON",
			# LIBCXX will try add these but we do this now so the try compile will work
			"CMAKE_EXE_LINKER_FLAGS": join_map_flags(target.ldflags, target.sysroot) + ' -nostdlib++',
			# This makes it too optimistic, and it tries to link lgcc and lgcc_s.
			#"CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY",
		}
		if target.llvmtarget.is_musl:
			opts["LIBCXX_HAS_MUSL_LIBC"] = "ON"

		if target.llvmtarget.is_baremetal:
			# LLVM uses this to test if linker script is available: 
			# https://github.com/llvm/llvm-project/blob/main/llvm/cmake/modules/HandleLLVMOptions.cmake#L135
			opts["UNIX"] = "1"

			# TODO: add option to enable locale in picolibc
			opts["LIBCXXABI_ENABLE_THREADS"] = "0"

			opts["LIBCXX_ENABLE_LOCALIZATION"] = "0"
			opts["LIBCXX_ENABLE_MONOTONIC_CLOCK"] = "0"
			opts["LIBCXX_ENABLE_THREADS"] = "0"
			opts["LIBCXX_ENABLE_FILESYSTEM"] = "0"

		if target.llvmtarget.is_mingw or target.llvmtarget.is_baremetal:
			# https://github.com/llvm/llvm-project/blob/0bc0edb847a0cc473a8b005c4725948de3306a20/libcxx/cmake/caches/MinGW.cmake
			# TODO: define __USE_MINGW_ANSI_STDIO (see above link)
			opts["LIBCXX_ENABLE_SHARED"] = "OFF"
			opts["LIBCXX_ENABLE_STATIC_ABI_LIBRARY"] = "ON"
			opts["LIBCXXABI_ENABLE_SHARED"] = "OFF"
			opts["LIBCXXABI_ENABLE_STATIC_UNWINDER"] = "ON"
			opts["LIBCXXABI_STATICALLY_LINK_UNWINDER_IN_STATIC_LIBRARY"] = "ON"


		super().__init__(target, files, "llvm-libcxx", ver, opts, srcdir)



# TODO separate package sources from package for eg llvm
# Also check for exclusive / canbuildmultipleatsametime, linux eg can't because it uses in-tree build
# Also todo run previous stages when install() called
