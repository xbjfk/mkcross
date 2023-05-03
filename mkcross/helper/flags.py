def join_map_flags(flags, sysroot, sep=' '):
	return sep.join(map(lambda x: x.format(sysroot=sysroot), flags))
