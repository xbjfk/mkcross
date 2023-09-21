def map_flags(flags, sysroot):
	return map(lambda x: x.format(sysroot=sysroot), flags)

def join_map_flags(flags, sysroot, sep=' '):
	return sep.join(map_flags(flags, sysroot))
