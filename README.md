# mkcross
mkcross is a super fast python toolkit to make linux and windows (mingw) toolchains in seconds
## Comparision (12900kf, aarch64-linux-musl)
| Program | Supported targets | Time to compile aarch64-linux-musl (including downloads) | program itself can run without being configured | Programmed in | Multi target in one command |
| -------------| ----- | ------------- | --- | -------- | --- |
| mkcross | Musl/Linux, Mingw/Windows, Picolibc/Baremetal | 30s (90s) | ✅ | **Python, C++** | ✅ |
| musl-cross-make | Musl/Linux | 176s (197s) | ✅ | Shell, Makefile | ❌ |
| crosstool-ng | uClibc/Linux GNU/Linux Newlib/Baremetal| N/A - no musl support | ❌ | Makefile | ❌ |

<!-- TODO: full blown comparision chart -->

# How to use
## Clang
Simply run clang like this:
```
clang --config-system-dir=[Path to sysroot]/etc/mkcross/clang
```
## CMake
Run cmake with `-DCMAKE_TOOLCHAIN_FILE=[Path to sysroot]/etc/mkcross/toolchain.cmake`

# How to make sysroot?
run `mkcross --target=<triple>`

# How?
 - LLVM is a cross compiler by nature. If you feed it the correct libraries, it will happily output what you want. This program will download and/or compile the needed libraries. There is no need to download/compile a whole compiler.

# Why?
 - No need to compile a gcc for your target
   - Much faster to compile just compiler-rt, libc, libc++ than binutils, gcc and libc.
   - No need to fiddle with binutils' and gcc's autoconf
 - No need to create a separate sysroot for every build machine, build is responsible for their own clang (ie the same sysroot can be downloaded for arm and x86 build machines).

# Notice
 - Baremetal support is currently in beta and might not even work!

# What's next?
 - [ ] Windows target support
   - [x] MingW
   - [ ] Proprietary (Visual Studio)
 - [ ] FreeBSD
   - [ ] Prebuilt (base.tar)
   - [ ] From sources (src.tar)
   - [ ] Mix (one of above + upstream LLVM)
 - [ ] MacOS target support
   - [ ] Some free software way
   - [ ] Proprietary (XCode.xip)
 - [ ] Linux
   - [x] musl
   - [ ] uclibc
   - [ ] glibc (cannot yet be built with clang)
 - [ ] Bare metal
 - [ ] Common libraries - zlib, curl, openssl
 - [ ] More architectures in compiler RT
   - [ ] Upstream to LLVM
 - [ ] Parallel download and source extraction
 - [ ] Parallel target generation
   - [ ] Will require copying autoconf/symlinking source files.
 - [ ] Query github api for source tarball size when download.
 - [ ] Better config and yaml config for target
 - [ ] Github actions to compile common targets
 - [ ] Meson support (depends on [this](https://github.com/mesonbuild/meson/discussions/11731))

# Notes
 - mingw targets are not abi compatible with gcc mingw! They are however compatible with MSVC, including C++, thanks to the efforts of Google.

# Troubleshooting tips
## I get errors when compiling c++ statically!
You need to link with libc++abi: `-lc++abi`
