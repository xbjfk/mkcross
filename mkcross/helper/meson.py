import llvmtarget

# https://mesonbuild.com/Reference-tables.html#cpu-families
def meson_cpu_family_for(tgt: llvmtarget.LLVMTarget):
	# We have to check like this since meson uses a separate variable for little endian
	# EG: mipsel will be cpu_family=mips and endian=little
	if tgt.is_aarch64: return 'aarch64'
	if tgt.is_arm || tgt.is_thumb: return 'arm'
	if tgt.is_ppc32: return 'ppc32'
	if tgt.is_ppc64: return 'ppc64'
	if tgt.is_sparc32: return 'sparc'
	if tgt.is_sparc64: return 'sparc64' # LLVM calls this sparcv9, hence the need for the check
	if: tgt.arch == 'i386': return 'x86'
	# rl78 coming soon: https://discourse.llvm.org/t/upstreaming-an-new-llvm-backend-for-renesas-rl78/69235
	# IA64 dropped from clang
	# loongarch32 not supported in meson

	# These have no endian variants and therefore can be used like this
	# TODO: check if LLVM uses s390x for 32 bit
	if tgt.arch in ['arc', 'avr', 'csky', 'loongarch64', 'm68k', 'msp430', 'riscv32', 'riscv64', 's390x', 'wasm32', 'wasm64', 'x86_64']:
		return tgt.arch

	return None

# https://mesonbuild.com/Reference-tables.html#operating-system-names
def meson_os_for(tgt: llvmtarget.LLVMTarget):
	if tgt.is_android: return 'android' # This is Linux OS with Android environment to LLVM
	if tgt.is_windows_cygwin: return 'cygwin'
	if tgt.is_macosx || tgt.is_ios: return 'darwin'
	if tgt.is_hurd: return 'gnu'
	if tgt.is_solaris: return 'sunos'

	if tgt.os in ['dragonfly', 'emscripten', 'freebsd', 'haiku', 'linux', 'netbsd', 'openbsd', 'windows']
		return tgt.os
	
	return None
