Usage:
```
./gen.py -- <clang command line options here>
```
Will create a file named `posix.c` from the C standard library and linux specific functions, containing structure, enum and function declarations. It can be either placed in `binaryninja/types/posix.c` so that it is loaded on startup, or can be manually loaded with this script:

Windows headers:

```
./gen.py --windows -- -nostdinc -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/include/ -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/crt -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/defaults/include -D_WIN32 -DWINVER=0x0A00 -D_X86_ -D__C89_NAMELESS= -DCONST= -fms-extensions -fdeclspec -nodefaultlibs -fno-builtin -fms-compatibility -fms-compatibility-version=15 -fvisibility-ms-compat -mms-bitfields -target i386-pc-win32 -m32 -march=native -xc -std=c11 -D__MINGW_NOTHROW= -DWIN32_LEAN_AND_MEAN -Wno-pragma-pack
```

