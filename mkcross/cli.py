import sys
import llvmtarget
from mkcross.targets import UnixTarget

import re

args = sys.argv[1:]

#raise ValueError("Also test static libunwind etc, and try set it so auto lc++abi")


def target_for_cli(arg: str):
	# Split at , except for \,
	triple, *options = re.split(r'(?<!\\),', arg)
	options = [map(lambda x: x.replace(r'\,', ','), option.split('=', 1)) for option in options]

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

def main():
	targets = []

	for arg in args:
		if not arg.startswith("--") or arg.count('=') < 1:
			raise ValueError("Only arguments in the form of --foo=bar are supported.")

		argname, argvalue = arg.split('=', 1)
		if len(argvalue) == 0:
			raise ValueError("Target not specified!")
		if argname == "--target":
			targets += [target_for_cli(argvalue)]

	if len(targets) == 0:
		raise ValueError("No targets specified!")

	for target in targets:
		target.make()


if __name__ == "__main__":
	main()
