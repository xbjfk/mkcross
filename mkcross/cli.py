import sys
import llvmtarget
from targets import UnixTarget

args = sys.argv[1:]

#raise ValueError("Also test static libunwind etc, and try set it so auto lc++abi")


def target_for_cli(arg: str):
	triple, *options = arg.split(',')
	options = [option.split('=') for option in options]
	if any(len(option) != 2 for option in options):
		raise ValueError("Invalid option provided! Options to targets must be in the form k1=v1,k2=v2")

	options = dict(options)

	print("Processed", arg, "to options", options)

	tgt = llvmtarget.LLVMTarget(triple)

	if tgt.os in UnixTarget.supported_os or tgt.is_mingw:
		t = UnixTarget(triple, tgt, options)
	else:
		raise ValueError(f"OS {tgt.os} not supported.")

	return t


def usage():
	print("Usage: " + sys.argv[0] + " [global arguments] target [target arguments] [target 2 [target 2 arguments] ... ]")

targets = []

for arg in args:
	if not arg.startswith("--") or arg.count('=') < 1:
		raise ValueError("Only arguments in the form of --foo=bar are supported.")

	argname, argvalue = arg.split('=', 1)
	if len(argvalue) == 0:
		raise ValueError("Target not specified!")
	if argname == "--target":
		targets += [target_for_cli(argvalue)]

for target in targets:
	target.make()

