import cfg
from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path
from shutil import which
from helper.flags import join_map_flags
import os
import tempfile

class TargetMeta(ABC):
	llvmtarget: str
	triple_nonnormalized: str
	sysroot: Path

	supported_os: List[str]
	target_options: Dict[str, str]

	cflags: List[str]
	cxxflags: List[str]
	ldflags: List[str]

	mkcross_config_dir: Path
	cross_file_cmake: Path

	def __init__(self, triple_nonnormalized, llvmtarget, config=[]):
		self.triple_nonnormalized = triple_nonnormalized
		self.llvmtarget = llvmtarget

		self.cflags = []
		self.cxxflags = []
		self.ldflags = []

		self.config = config

		self.check_sanity_or_throw()

		self.sysroot = cfg.outputpath / triple_nonnormalized # TODO make sure no duplicate target names

		self.configure(config)

		self.mkcross_config_dir = self.sysroot / "etc/mkcross"
		self.mkcross_config_dir.mkdir(parents=True, exist_ok=True)
		self.create_toolchain_files()


	def create_toolchain_files(self):
		clangdir = self.mkcross_config_dir / "clang"
		clangdir.mkdir(parents=True, exist_ok=True)
		
		for file, args in [("clang", self.cflags + self.ldflags), ("clang++", self.cxxflags + self.ldflags), ("clang-cpp", self.cflags + self.cxxflags) ]:
			with open(str(clangdir / file) + ".cfg", "w") as f:
				args = set(args)
				root_from_clang = os.path.relpath(self.sysroot, start = clangdir)
				f.write(join_map_flags(args, "<CFGDIR>/" + str(root_from_clang), sep='\n'))
				f.write('\n')
				f.flush()
			

		root_from_config = os.path.relpath(self.sysroot, start = self.mkcross_config_dir)

		cross_file_meson = self.mkcross_config_dir / "meson-cross.ini"

		# TODO: use XDG_DATA_DIRS to specify without full path
		with open(cross_file_meson, "w") as f:
			f.write(f"""[constants]
mkcross_sysroot = '../../'
mkcross_triple = '{self.llvmtarget.triplestr}'

[host_machine]
system = '{self.llvmtarget.os}'

[properties]
sys_root = mkcross_sysroot

[binaries]
c = {which("clang")}
objc = {which("clang")}
cpp = {which("clang++")}
objcpp = {which("clang++")}
c_ld = 'lld'
cpp_ld = 'lld'
ar = {which("llvm-ar")}
nm = {which("llvm-nm")}
ranlib = {which("llvm-ranlib")}
strip = {which("llvm-strip")}
windres = {which("llvm-rc")}

[built-in options]
pkg_config_path = mkcross_sysroot + '/usr/lib/pkgconfig'
c_args = ['{join_map_flags(self.cflags, "../../")}]
cpp_args = ['{join_map_flags(self.cxxflags, "../../")}]
c_link_args = ['{join_map_flags(self.ldflags, "../../")}]
cpp_link_args = ['{join_map_flags(self.ldflags, "../../")}]
""")
			if self.llvmtarget.is_mingw:
				f.write("default_library = 'static'\n")
			f.flush()
		


		self.cross_file_cmake = self.mkcross_config_dir / "toolchain.cmake"

		with open(self.cross_file_cmake, "w") as f:
			f.write(f"""set(CMAKE_SYSTEM_NAME {self.cmake_system_name})
set(CMAKE_SYSTEM_VERSION 1)
set(CMAKE_SYSTEM_PROCESSOR {self.llvmtarget.arch})

set(mkcross_SYSROOT "${{CMAKE_CURRENT_LIST_DIR}}/{root_from_config}")
set(mkcross_TRIPLE {self.llvmtarget.triplestr})

set(CMAKE_SYSROOT ${{mkcross_SYSROOT}})

set(CMAKE_C_COMPILER {which("clang")})
set(CMAKE_CXX_COMPILER {which("clang++")})
set(CMAKE_AR {which("llvm-ar")})
# TODO: maybe dlltool needs arc specified?
set(CMAKE_DLLTOOL {which("llvm-dlltool")})
set(CMAKE_NM {which("llvm-nm")})
set(CMAKE_OBJCOPY {which("llvm-objcopy")})
set(CMAKE_OBJDUMP {which("llvm-objdump")})
set(CMAKE_RANLIB {which("llvm-ranlib")})
set(CMAKE_RC_COMPILER {which("llvm-windres")})
set(CMAKE_READELF {which("llvm-readelf")})
set(CMAKE_STRIP {which("llvm-strip")})

set(CMAKE_C_COMPILER_TARGET ${{mkcross_TRIPLE}})
set(CMAKE_CXX_COMPILER_TARGET ${{mkcross_TRIPLE}})
set(CMAKE_ASM_COMPILER_TARGET ${{mkcross_TRIPLE}})


set(common_ldflags "{join_map_flags(self.ldflags, "${mkcross_SYSROOT}")}")

set(CMAKE_C_FLAGS_INIT "{join_map_flags(self.cflags, "${mkcross_SYSROOT}")}")
set(CMAKE_CXX_FLAGS_INIT "{join_map_flags(self.cxxflags, "${mkcross_SYSROOT}")}")
set(CMAKE_ASM_FLAGS_INIT "{join_map_flags(self.cflags, "${mkcross_SYSROOT}")}")
set(CMAKE_RC_FLAGS_INIT "-I ${{mkcross_SYSROOT}}/include --target={self.llvmtarget.triplestr}")


set(CMAKE_EXE_LINKER_FLAGS_INIT ${{common_ldflags}})
set(CMAKE_MODULE_LINKER_FLAGS_INIT ${{common_ldflags}})
set(CMAKE_SHARED_LINKER_FLAGS_INIT ${{common_ldflags}})
#CMAKE_STATIC_LINKER_FLAGS is passed to ar, not clang
""")
			f.flush()



	@abstractmethod
	def configure(self, config):
		return NotImplemented

	@abstractmethod
	def check_sanity_or_throw(self):
		return NotImplemented

	@abstractmethod
	def get_packages_list(self):
		return NotImplemented

	@abstractmethod
	def make(self):
		return NotImplemented
