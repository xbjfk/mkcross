# mkcross
mkcross is a super fast python toolkit to make linux and windows (mingw) toolchains in seconds
## Comparision (12900kf, aarch64-linux-musl)
| Program | Supported targets | Time to compile aarch64-linux-musl (including downloads) | program itself can run without being configured | Programmed in | Multi target in one command |
| -------------| ----- | ------------- | --- | -------- | --- |
| mkcross | Musl/Linux, Mingw/Windows, Picolibc/Baremetal | 30s (90s) | ✅ | **Python, C++** | ✅ |
| musl-cross-make | Musl/Linux | 176s (197s) | ✅ | Shell, Makefile | ❌ |
| crosstool-ng | uClibc/Linux GNU/Linux Newlib/Baremetal| N/A - no musl support | ❌ | Makefile | ❌ |

<!-- TODO: full blown comparision chart -->

## Features
 - Extremely fast.
 - Portable sysroots - you can `mv` the sysroot anywhere you want and it will still work.
 - Supports Windows, Linux, Baremetal, and - experimentally - WasiX.
 - Supports every architecture LLVM supports.
 - No need to compile a whole compiler for your target
   - Much faster to compile just compiler-rt, libc, libc++ than binutils, gcc and libc.
   - No need to fiddle with binutils' and gcc's autoconf
 - Sysroots can be used on any machine with clang and LLVM tools installed.

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

# Notice
 - wasix support is currently highly experimental
 - baremetal c++ is WIP and may not work on every architecture.

# What's next?
 - [x] WasiX support (**EXPERIMENTAL**)
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
 - [X] Bare metal (**EXPERIMENTAL**)
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
You need to link with more c++ libs: `-lc++abi` and potentially `-lunwind`
## relocation R_RISCV_HI20 out of range: 524288 is not in [-524288, 524287];
You cant compile with LTO. I need to investigate this further.
If you care about the details, see [this blog post](https://www.sifive.com/blog/all-aboard-part-4-risc-v-code-models#what-does--mcmodelmedlow-mean)
## strtoll_l strtoull_l strtof_l strtod_l strtold_l etc. are undefined on picolibc:
Add -D_GNU_SOURCE to your defines.
