import warnings
import tempfile
from shutil import which
from typing import List

import shlex

from mkcross.helper import latest_version
from mkcross.packages import CompilerRT, LibCXX, Libunwind, Linux, Musl, MingwHeaders, Mingw, CppWinRT, ClangResourceHeaders, PicoLibc, WasixLibc
from mkcross.targets.targetmeta import TargetMeta


class UnixTarget(TargetMeta):
	__LINUX_ARCHES = {"arm", "armeb", "aarch64", "aarch64_be", "aarch64_32", "csky", "hexagon", "m68k", "mips", "mipsel", "mips64", "mips64el", "powerpc", "powerpcle", "powerpc64", "powerpc64le", "riscv32", "riscv64", "sparc", "sparcv9", "sparcel", "s390x", "thumb", "thumbeb", "i386", "x86_64", "loongarch32", "loongarch64"}

	# https://github.com/llvm/llvm-project/blob/main/compiler-rt/cmake/Modules/AllSupportedArchDefs.cmake
	__CRT_SUPPORTED_ARCHES = {"aarch64", "arm", "thumb",
		"hexagon", "i386", "x86_64",
		"loongarch64", "mips", "mipsel",
		"mips64", "mips64el", "powerpc",
		# No support for 32 bit ppc le
		"powerpc64", "powerpc64le",
		"riscv32", "riscv64",
		"s390x", "sparc", "sparcv9",
		"wasm32", "wasm64", "ve"}  # TODO: check armeb

	__MUSL_ARCHES = {"i386", "x86_64",
					"arm", "armeb", "aarch64",
					"aarch64_be", "mips", "mipsel",
					"mips64", "mips64el", "powerpc",
					"powerpcle",
					"powerpc64", "powerpc64le", "riscv64",
					"s390x", "m68k", "thumb",
					"thumbeb"}

	supported_os = {
		# "dragonfly",
		# "freebsd",
		"linux",
		"wasi",
		# "netbsd",
		# "openbsd",
		# "haiku",
		# "minix",
		# "rtems",
		# PS3 and 4?
		# "contiki",
		# "hurd"

		"windows", #MingW
		"none",
	}

	# TODO:FREEBSD brebuilt (base.txz) and source (src.txz)

	def check_sanity_or_throw(self):
		# Kernel checks.
		# TODO: xtensa is coming to LLVM soon
		# TODO: centralized dictionary for this.
		if self.llvmtarget.is_linux:
			if self.llvmtarget.arch not in self.__LINUX_ARCHES:
				raise ValueError(f"Architecture {self.llvmtargetarch} not supported in Linux")

			if self.llvmtarget.arch not in self.__CRT_SUPPORTED_ARCHES:
				raise ValueError(f"Architecture {self.llvmtargetarch} not supported in Compiler-RT")

			if not self.llvmtarget.is_musl:
				raise ValueError("Only musl libc is supported for now (glibc cannot be compiled with Clang)")

			if self.llvmtarget.is_musl:
				# Musl doesn't support ILP32 aarch64
				if self.llvmtarget.arch not in self.__MUSL_ARCHES:
					raise ValueError(f"Architecture {self.llvmtarget.arch} not supported using Musl Libc!")

		elif self.llvmtarget.is_mingw:
			# arm32 does not compile for me for some reason.
			if self.llvmtarget.arch not in ["i386", "x86_64", "aarch64"]:
				raise ValueError(f"Architecture {self.llvmtarget.arch} not supported in Windows/Mingw!")


		elif self.llvmtarget.is_baremetal:
			if self.llvmtarget.environment == "unknown":
				raise ValueError("Unknown environment! You probably want something like ARCH-unknown-none-elf")

			# You need to specify an oslib to link
			warnings.warn("You are using a baremetal target. mkcross' bare metal uses picolibc. When linking with picolibc, you need to override the default variables for flash location and such, with either a linker script or manually. You may also need to link an oslib that specifies the stdin/stdout/stderr files. Please see the picolibc GitHub repository for more information.")

			self.can_link = False

			return

		elif self.llvmtarget.is_wasi and self.llvmtarget.vendor == "wasix":
			return

		else: raise ValueError("This target is not supported.")

	def configure(self, config):
		cxxonlyflags = []
		c_and_ldflags = []


		cflags_init = shlex.split(config.get('cflags'))
		if cflags_init is None:
			self.cflags += ['-Os']
		else:
			self.cflags += cflags_init


		ldflags_init = shlex.split(config.get('ldflags'))
		if cflags_init is not None:
			self.ldflags += ldflags_init

		# no-default-config prevents some distro settings that could be incompatible
		self.cflags += ['--no-default-config']

		fpu = config.get('fpu')
		if fpu is not None:
			self.cflags += [f'-mfpu={fpu}']

		abi = config.get("abi")
		if abi is not None:
			self.cflags += [f'-mabi={abi}']

		cpu = config.get("cpu")
		if cpu is not None:
			self.cflags += [f'-mcpu={cpu}']

		if self.llvmtarget.is_wasi:
			self.cflags += ['-ftls-model=local-exec', '-D_WASI_EMULATED_MMAN', '-D_WASI_EMULATED_PROCESS_CLOCKS', '-DNDEBUG', '-mbulk-memory', '-fno-trapping-math']
			cxxonlyflags += ['-fno-exceptions']
			self.ldflags += ['-lwasi-emulated-mman', '-lwasi-emulated-process-clocks', '-lwasi-emulated-getpid']

		target_features = config.get("target_features")
		if target_features is not None:
			if target_features[0] == '+':
				target_features = target_features[1:]

				for feature in target_features.split('+'):
					self.cflags += [f"-m{feature}"]

				# Clang does not define this, GCC does and musl expects it.
				if feature == "soft-float" and self.llvmtarget.is_ppc:
					self.cflags += ["-D_SOFT_FLOAT"]


		if self.llvmtarget.is_mips:
			# https://github.com/llvm/llvm-project/issues/58377
			# https://reviews.llvm.org/D80392
			# https://github.com/ziglang/zig/issues/4925
			self.ldflags += ['-Wl,-z,notext']

		c_and_ldflags += [
			"--no-default-config",  # Disable distro defaults
			f"--target={self.llvmtarget.triplestr}",
			"--sysroot={sysroot}",
			"-resource-dir", "{sysroot}/lib/clang" # THIS IS A CFLAGS TOO!
		]

		self.ldflags += [
			"-fuse-ld=lld",  # Use LLD
			"--rtlib=compiler-rt",
			"--unwindlib=libunwind",
			"--stdlib=libc++",
		]


		cxxonlyflags += [
			"--stdlib=libc++",
		]


		self.cflags += c_and_ldflags
		self.ldflags += c_and_ldflags

		self.cxxflags = self.cflags + cxxonlyflags

		# Wasi = linux works best - https://github.com/WebAssembly/wasi-sdk/issues/181
		self.cmake_system_name = "WASI" if self.llvmtarget.is_wasi else ("Linux" if self.llvmtarget.is_linux else ("Generic" if self.llvmtarget.is_baremetal else "Windows"))

		if self.llvmtarget.is_wasi:
			wasi_platform = self.sysroot / "etc/mkcross/cmake/Platform/WASI.cmake"
			wasi_platform.parents[0].mkdir(parents=True, exist_ok=True)
			with open(wasi_platform, 'w') as f:
				# Unix is mkcross only, not in wasi-sdk and such, but it makes programs happy
				f.write("""
set(WASI 1)
set(UNIX 1)
""")


	def make(self):
		pkg = ClangResourceHeaders(self)
		pkg.install()

		if self.llvmtarget.is_linux:
			ver = self.config.get("linux_ver") or Linux.get_latest_version()
			pkg = Linux(self, ver, headers_only=True)
			pkg.download()
			pkg.prepare()
			pkg.build()
			pkg.install()

			# TODO use install_headers() instead of separate thing
			ver = self.config.get("musl_ver") or Musl.get_latest_version()
			pkg = Musl(self, ver, headers_only=True)
			musl = pkg
			pkg.download()
			pkg.prepare()
			pkg.configure()
			pkg.build()
			pkg.install()

		elif self.llvmtarget.is_mingw:
			ver = "10.0.0" # TODO: unhardcode
			pkg = MingwHeaders(self, ver)
			pkg.download()
			pkg.prepare()
			pkg.configure()
			pkg.build()
			pkg.install()

			pkg = Mingw(self, ver)
			pkg.download()
			pkg.prepare()
			pkg.configure()
			pkg.build()
			pkg.install()

		elif self.llvmtarget.is_wasm:
			pkg = WasixLibc(self)
			pkg.download()
			pkg.prepare()
			pkg.configure()
			pkg.build()
			pkg.install()

		elif self.llvmtarget.is_baremetal:
			ver = self.config.get("picolibc_ver") or PicoLibc.get_latest_version()
			pkg = PicoLibc(self, ver)
			pkg.download()
			pkg.prepare()
			pkg.configure()
			pkg.build()
			pkg.install()


		ver = self.config.get("llvm_ver") or latest_version.llvm()

		pkg = CompilerRT(self, ver)
		pkg.download()
		pkg.prepare()
		pkg.configure()
		pkg.build()
		pkg.install()

		if self.llvmtarget.is_linux:
			musl.headers_only = False
			pkg = musl
			# Must reconfigure to make it aware of new compiler-rt
			pkg.configure()
			pkg.build()
			pkg.install()


		if not self.llvmtarget.is_wasm:
			pkg = Libunwind(self, ver)
			pkg.download()
			pkg.prepare()
			pkg.configure()
			pkg.build()
			pkg.install()

		pkg = LibCXX(self, ver)
		pkg.download()
		pkg.prepare()
		pkg.configure()
		pkg.build()
		pkg.install()


		return

		# I don't know what this is but it builds
		if ismingw and self.config.get("build_cppwinrt", False):
			ver = "2.0.230225.1"
			pkg = CppWinRT(self, ver)
			pkg.download()
			pkg.prepare()
			pkg.configure()
			pkg.build()
			pkg.install()

	def get_packages_list(self):
		return []

