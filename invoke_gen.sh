#!/usr/bin/bash

if [ -z "$1" ]; then
  echo "Please supply either x86_64 or x86 as the first argument"
  exit 0
fi

if [ "$1" = "x86_64" ]; then
  ./gen.py --windows -- -nostdinc -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/include/ -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/crt -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/defaults/include -D_WIN64 -DWINVER=0x0A00 -D__X86_64 -D__C89_NAMELESS= -DCONST= -fms-extensions -fdeclspec -nodefaultlibs -fno-builtin -fms-compatibility -fms-compatibility-version=15 -fvisibility-ms-compat -mms-bitfields -target x86_64-pc-win -m64 -march=native -xc -std=c11 -D__MINGW_NOTHROW= -DWIN32_LEAN_AND_MEAN -Wno-pragma-pack -D__USE_W32_SOCKETS
else
  ./gen.py --windows -- -nostdinc -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/include/ -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/crt -I/vm/mingw-w64-v5.0.3/mingw-w64-headers/defaults/include -D_WIN32 -DWINVER=0x0A00 -D_X86_ -D__C89_NAMELESS= -DCONST= -fms-extensions -fdeclspec -nodefaultlibs -fno-builtin -fms-compatibility -fms-compatibility-version=15 -fvisibility-ms-compat -mms-bitfields -target i386-pc-win32 -m32 -march=native -xc -std=c11 -D__MINGW_NOTHROW= -DWIN32_LEAN_AND_MEAN -Wno-pragma-pack -D__USE_W32_SOCKETS
fi

