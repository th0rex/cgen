#!/usr/bin/python

from clang.cindex import *

# Default header files {{{
std_files = [
    "assert.h",
    "complex.h",
    "ctype.h",
    "errno.h",
    "fenv.h",
    "float.h",
    "inttypes.h",
    "iso646.h",
    "limits.h",
    "locale.h",
    "math.h",
    "setjmp.h",
    "signal.h",
    "stdalign.h",
    "stdarg.h",
    "stdatomic.h",
    "stdbool.h",
    "stddef.h",
    "stdint.h",
    "stdio.h",
    "stdlib.h",
    "stdnoreturn.h",
    "string.h",
    "tgmath.h",
    "threads.h",
    "time.h",
    "uchar.h",
    "wchar.h",
    "wctype.h",
]

linux_files = [
    "dirent.h"
    "sys/acct.h",
    "sys/acl.h",
    #"sys/asoundlib.h",
    "sys/auxv.h",
    "sys/bitypes.h",
    "sys/capability.h",
    "sys/cdefs.h",
    "sys/debugreg.h",
    "sys/dir.h",
    "sys/elf.h",
    "sys/epoll.h",
    "sys/errno.h",
    "sys/eventfd.h",
    "sys/fanotify.h",
    "sys/fcntl.h",
    "sys/file.h",
    "sys/fsuid.h",
    "sys/gmon.h",
    "sys/gmon_out.h",
    "sys/inotify.h",
    "sys/ioctl.h",
    "sys/io.h",
    "sys/ipc.h",
    "sys/kd.h",
    "sys/klog.h",
    "sys/mman.h",
    "sys/mount.h",
    "sys/msg.h",
    "sys/mtio.h",
    "sys/param.h",
    "sys/pci.h",
    "sys/perm.h",
    "sys/personality.h",
    "sys/poll.h",
    "sys/prctl.h",
    "sys/procfs.h",
    "sys/profil.h",
    "sys/ptrace.h",
    "sys/queue.h",
    "sys/quota.h",
    "sys/random.h",
    "sys/raw.h",
    "sys/reboot.h",
    "sys/reg.h",
    "sys/resource.h",
    "sys/select.h",
    "sys/sem.h",
    "sys/sendfile.h",
    "sys/shm.h",
    "sys/signalfd.h",
    "sys/signal.h",
    "sys/socket.h",
    "sys/socketvar.h",
    "sys/soundcard.h",
    "sys/statfs.h",
    "sys/stat.h",
    "sys/statvfs.h",
    "sys/stropts.h",
    "sys/swap.h",
    "sys/syscall.h",
    "sys/sysctl.h",
    "sys/sysinfo.h",
    "sys/syslog.h",
    "sys/sysmacros.h",
    "sys/termios.h",
    "sys/timeb.h",
    "sys/time.h",
    "sys/timerfd.h",
    "sys/times.h",
    "sys/timex.h",
    "sys/ttychars.h",
    "sys/ttydefaults.h",
    "sys/types.h",
    "sys/ucontext.h",
    "sys/uio.h",
    "sys/un.h",
    "sys/unistd.h",
    "sys/user.h",
    "sys/ustat.h",
    "sys/utsname.h",
    "sys/vfs.h",
    "sys/vlimit.h",
    "sys/vm86.h",
    "sys/vt.h",
    "sys/vtimes.h",
    "sys/wait.h",
    "sys/xattr.h",
]

# }}}


def parse_args():
    import sys
    is_linux = True
    in_clang_args = False
    clang_args = []
    dirs = []
    for arg in sys.argv[1:]:
        if arg == "--":
            in_clang_args = True
            continue
        elif arg == "--windows":
            is_linux = False
            continue

        if in_clang_args:
            clang_args.append(arg)
        else:
            dirs.append(arg)

    return (dirs, clang_args, is_linux)


def create_dummy_file(dirs, is_linux):
    import os

    with open("dummy.c", mode="w") as dummy:
        files = [
            f for d in dirs for f in os.listdir(d)
            if os.path.isfile(os.path.join(d, f))
        ]
        if is_linux:
            files = files + [
                os.path.join("/usr/include/", f) for f in std_files
            ]
            files = files + [
                os.path.join("/usr/include/", f) for f in linux_files
            ]

        if not is_linux:
            dummy.write("""#include "basetsd.h"\n""")
            dummy.write("""#include "minwindef.h"\n""")
            dummy.write("""#include "winsock2.h"\n""")
            dummy.write("""#include "windows.h"\n""")
            dummy.write("""#include "winuser.h"\n""")
        else:
            for f in files:
                dummy.write("""#include "{}"\n""".format(f))


def get_decls(tu, is_linux):
    def base_type(t):
        while t.kind == TypeKind.POINTER:
            t = t.get_pointee()
        return t

    def blocked(t):
        tbl = [
            TypeKind.COMPLEX,
            TypeKind.INT128,
            TypeKind.WCHAR,
            TypeKind.UINT128,
            TypeKind.FLOAT128,
            TypeKind.HALF,
            TypeKind.NULLPTR,
            TypeKind.OVERLOAD,
            TypeKind.DEPENDENT,
            TypeKind.LVALUEREFERENCE,
            TypeKind.RVALUEREFERENCE,
        ]
        return t.kind in tbl

    def resolve_type(t):
        return t.get_canonical()

    def format_type(t,
                    n=None,
                    expand=False,
                    resolve=False,
                    in_typedef_resolve=False,
                    print_struct_name=True,
                    c=None):
        fmt = "{}{}".format("const "
                            if t.is_const_qualified() else "", "volatile "
                            if t.is_volatile_qualified() else "")
        n = " " + n if n != None and print_struct_name else ""
        if c is None:
            c = t.get_declaration()
        # TODO: make this nicer
        if c.type.kind == TypeKind.ELABORATED:
            c = t.get_declaration()
        if t.kind == TypeKind.ELABORATED and expand and c.displayname == "":
            t = c.type

        # wtf
        if t.kind == TypeKind.INT and n is not None and n == " size_t":
            return fmt + "size_t"

        if t.kind == TypeKind.VOID and in_typedef_resolve:
            return "void* " + n

        tbl = {
            TypeKind.VOID: "void",
            TypeKind.BOOL: "bool",
            TypeKind.CHAR_U: "char",
            TypeKind.UCHAR: "unsigned char",
            TypeKind.USHORT: "unsigned short",
            TypeKind.UINT: "unsigned int",
            TypeKind.ULONG: "unsigned long",
            TypeKind.ULONGLONG: "unsigned long long",
            TypeKind.CHAR_S: "char",
            TypeKind.SCHAR: "signed char",
            TypeKind.SHORT: "short",
            TypeKind.INT: "int",
            TypeKind.LONG: "long",
            TypeKind.LONGLONG: "long long",
            TypeKind.FLOAT: "float",
            TypeKind.DOUBLE: "double",
            TypeKind.LONGDOUBLE: "long double",
        }

        if t.kind == TypeKind.POINTER:
            pt = t.get_pointee()
            c = pt.get_declaration()
            if in_typedef_resolve and (c.kind == CursorKind.STRUCT_DECL
                                       or c.kind == CursorKind.UNION_DECL):
                ty = "struct"
                if c.kind == CursorKind.UNION_DECL:
                    ty = "union"
                # Not a real declaration
                if c.canonical == c and c.displayname != "":
                    return "{} {}* {}".format(ty, c.displayname, n)
                # Not that much we can do since bn doesn't support typedef struct A{int b;}* C;
                else:
                    return "void* {}".format(n)
            if pt.kind == TypeKind.FUNCTIONPROTO or pt.kind == TypeKind.FUNCTIONNOPROTO:
                return "{}(*{})({})".format(
                    format_type(pt.get_result(), expand=expand), n, ", ".join([
                        format_type(t, expand=expand)
                        for t in pt.argument_types()
                    ]))
            elif pt.kind == TypeKind.UNEXPOSED:
                return format_type(pt, expand=expand, n=n[1:])
            elif c.kind == CursorKind.ENUM_DECL:
                # bn can't do this yet
                return "void* {}".format(n)
            return format_type(t.get_pointee(), expand=expand, in_typedef_resolve=in_typedef_resolve) + "*" + \
                (" const" if t.is_const_qualified() else "") + \
                (" volatile" if t.is_volatile_qualified() else "") + \
                n
        elif t.kind == TypeKind.TYPEDEF and resolve:
            if t.get_canonical().kind == TypeKind.FUNCTIONPROTO:
                # Fuck gnu libc for using this feature
                return ""
            cano = t.get_canonical()
            #print(t.get_declaration().get_definition().type.kind, t.get_declaration().underlying_typedef_type.displayname)
            return "typedef {};".format(
                format_type(
                    t.get_declaration().underlying_typedef_type,
                    n=t.get_typedef_name(),
                    expand=True,
                    in_typedef_resolve=True))
        elif t.kind == TypeKind.RECORD:
            ty = "struct"
            if c.kind == CursorKind.UNION_DECL:
                ty = "union"

            fields = list(t.get_fields())

            if len(fields) == 0:
                fields_str = "void* __unused;\n"
            else:
                fields_str = "".join([
                    format_type(
                        c.type,
                        c=c,
                        expand=expand,
                        n=c.displayname,
                        in_typedef_resolve=True) + ";\n" for c in fields
                ])

            return "{}{}{{\n{}}}{}".format(
                ty,
                # TODO: fix this line so we can remove the extra struct handling in typedefs
                n if not in_typedef_resolve else
                (" " + c.displayname
                 if in_typedef_resolve and c.displayname != "" else ""),
                fields_str,
                n if in_typedef_resolve else "")
        elif t.kind == TypeKind.TYPEDEF:
            return fmt + t.get_typedef_name() + n
        elif t.kind == TypeKind.INCOMPLETEARRAY:
            return format_type(
                t.element_type, expand=expand,
                print_struct_name=False) + n + "[1]"
        elif t.kind == TypeKind.CONSTANTARRAY:
            return format_type(
                t.element_type, expand=expand,
                print_struct_name=False) + n + "[{}]".format(t.element_count)
        elif t.kind == TypeKind.ELABORATED:
            return t.spelling + n
        elif c.kind == CursorKind.ENUM_DECL:
            return "enum{}{{\n{}\n}}{}".format(
                n if not in_typedef_resolve else "",
                # TODO: cleanup when bn supports negative enum values
                ",\n".join([
                    "{} = {}".format(
                        x.displayname, x.enum_value if x.enum_value >= 0 else
                        2**(8 * c.enum_type.get_size()) - x.enum_value)
                    for x in c.get_children()
                ]),
                n if in_typedef_resolve else "")
        elif t.kind in tbl:
            if c.is_bitfield() and c.displayname == "":
                return fmt + tbl[t.kind] + " padding_{}".format(
                    c.get_field_offsetof())
            # TODO: enable when binaryninja supports bitfields
            #elif c.is_bitfield():
            #    return fmt + tbl[t.kind] + "{}:{}".format(n, c.get_bitfield_width())
            return fmt + tbl[t.kind] + n
        elif t.kind == TypeKind.UNEXPOSED:
            s = t.spelling
            idx = s.find("(")
            r = s[:idx] + "(*" + n + ")" + s[idx:]
            print("UNEXPOSED", t.spelling, "------- Patched", r)
            return r

        if t.kind == TypeKind.FUNCTIONNOPROTO:
            # fuck windows
            # WE HAVE TO HANDLE THIS?!
            print("------------------- UNHANDLED ", t.spelling)
            if "BSTR" in t.spelling:
                "void*"  # TODO: please help me
            elif "VARIANT_BOOL" in t.spelling:
                return "short"
            elif "int" in t.spelling:
                return "int"
            #elif "struct _HTTP_VERSION" in t.spelling:
            #    # WHAT THE FUCK DO I DO
            return ""

        print("Not handled: ", t.kind, ": ", t.spelling)
        assert (False)

    def iter_children(i, t, sts):
        if t.kind == TypeKind.ELABORATED:
            t = t.get_declaration().type

        if t.kind == TypeKind.RECORD:
            decl = t.get_declaration()
            sts.append((i - 1, decl))
        elif t.kind == TypeKind.TYPEDEF:
            iter_children(i, t.get_canonical(), sts)

    assert (tu.cursor.kind.is_translation_unit())
    forwards = []
    structs = []
    functions = []
    typedefs = []
    enums = []
    already = set()
    # Sadly the clang API doesn't expose the noreturn attribute
    no_return = [
        "exit", "_exit", "__stack_chk_fail", "pthread_exit", "abort", "err",
        "verr", "quick_exit", "_Exit", "errc", "verrc", "errx", "verrx",
        "__longjmp_chk", "longjmp", "siglongjmp"
    ]
    for i, c in enumerate(tu.cursor.get_children()):
        if c.kind == CursorKind.STRUCT_DECL:
            if c.canonical == c:
                # Forward decl:
                forwards.append((i, c))
            else:
                structs.append((i, c))
        elif c.kind == CursorKind.TYPEDEF_DECL:
            iter_children(i, c.type, structs)
            typedefs.append((i, c))
        elif c.kind == CursorKind.ENUM_DECL:
            enums.append((i, c))
        if not (c.kind.is_declaration()
                and c.kind == CursorKind.FUNCTION_DECL):
            continue
        ft = c.type
        if ft.kind != TypeKind.FUNCTIONPROTO and ft.kind != TypeKind.FUNCTIONNOPROTO:
            print("no function proto ", c.kind, "---", ft.kind, "---",
                  c.displayname, "---", c.spelling, "---", ft.spelling)
            continue
        assert (ft.kind == TypeKind.FUNCTIONPROTO
                or ft.kind == TypeKind.FUNCTIONNOPROTO)
        if blocked(ft.get_result()):
            continue

        if c.displayname in already:
            continue
        already.add(c.displayname)

        if c.linkage != LinkageKind.EXTERNAL:
            #print("Ignoring linkage:", c.linkage)
            continue

        args = []
        cont = False
        for p in c.get_arguments():
            assert (p.kind == CursorKind.PARM_DECL)
            a = p.type
            if blocked(a):
                cont = True
                break

            name = p.mangled_name
            if len(name) > 0 and name[0] == "_" and not is_linux:
                name = name[1:]

            args.append(format_type(a, n=name))

        if ft.kind == TypeKind.FUNCTIONPROTO and ft.is_function_variadic():
            args.append("...")

        if cont:
            continue

        ret_type = format_type(ft.get_result())

        name = c.mangled_name
        if "@" in name:
            name = c.mangled_name[:name.find("@")]
        if name[0] == "_" and not is_linux:
            name = name[1:]

        if is_linux:
            functions.append((i, "{} {}({}){};".format(
                ret_type, name, ",".join(args), " __noreturn"
                if name in no_return else "")))
        else:
            # Assume stdcall lul
            cc = "__stdcall"
            if any("__cdecl" in x.spelling for x in c.get_tokens()):
                cc = "__cdecl"
            functions.append((i, "{} {} {}({}){};".format(
                ret_type, cc, name, ",".join(args), " __noreturn"
                if name in no_return else "")))

    # Expand typedefs and add references to structs.
    tds = []
    block = [
        "int8_t",
        "uint8_t",
        "int16_t",
        "uint16_t",
        "int32_t",
        "uint32_t",
        "size_t",
        "offset_t",
        "int64_t",
        "uint64_t",
        "ssize_t",

        # Windows shit
        "LPOLESTREAMVTBL",
    ]
    if is_linux:
        block.append("uintptr_t")
    else:
        block.append("ptrdiff_t")
    replace = {
        "locale_t": "typedef struct __locale_struct* locale_t;",
        "sigval_t": "typedef __sigval_t sigval_t;",
        "stack_t": "typedef struct { void* __unused; } stack_t;",
        "_IO_lock_t": "typedef void* _IO_lock_t;",
    }
    already = set()
    for i, td in typedefs:
        tdn = td.type.get_typedef_name()
        if tdn in block:
            continue
        elif tdn in replace:
            already.add(tdn)
            tds.append((i, replace[tdn]))
            continue
        # TODO: remove once bn can do "typedef (struct|union|enum) a a;"
        elif tdn == td.type.get_canonical().get_declaration().displayname:
            already.add(tdn)
            continue
        if tdn in already:
            continue
        already.add(tdn)

        tds.append((i, format_type(td.type, resolve=True)))

    strcts = []
    already = set()
    for i, st in structs:
        if st.displayname == "":
            continue
        if st.displayname in already:
            continue
        # Can be removed once bn supports empty structs/unions:
        if len(list(st.type.get_fields())) == 0:
            already.add(st.displayname)
            strcts.append((i, "{} {} {{ void* __unused; }};".format(
                "struct" if st.kind == CursorKind.STRUCT_DECL else "union",
                st.displayname)))
            continue
        already.add(st.displayname)
        strcts.append(
            (i, format_type(st.type, n=st.displayname, expand=True) + ";"))

    already = set()
    enms = []
    for i, en in enums:
        if en.displayname == "":
            continue
        enms.append(
            (i, format_type(en.type, n=en.displayname, expand=True) + ";"))

    already = set()
    fwds = []
    for i, fw in forwards:
        if fw.displayname == "":
            continue
        fwds.append((i, "struct {};".format(fw.displayname)))

    return functions, strcts, tds, enms, fwds


def main():
    dirs, clang_args, is_linux = parse_args()
    create_dummy_file(dirs, is_linux)

    index = Index.create()
    tu = index.parse("dummy.c", args=clang_args)

    if is_linux:
        output = open("posix.c", "w")
    else:
        output = open("windows.c", "w")

    if not is_linux:
        output.write("""
        // This appears nowhere in the headers as a forward decl.
        // It appears as a member in a struct but that doesn't globally forward declare it, right?
        struct _ACTIVATION_CONTEXT;
        // Same
        struct lconv;
        """)

    fns, structs, typedefs, enums, fwds = get_decls(tu, is_linux)
    # TODO: build tree and return it so that we can print them in proper order
    xs = sorted(fns + typedefs + structs + enums + fwds, key=lambda i: i[0])

    output.write("struct __locale_data { void* __unused; };\n")
    blck = [
        "IRpcChannel",
        "IRpcStub",
        "I_RpcServerInqAddressChangeFn",
        "_MIDL_STUB_DESC",
        "RpcSmSwapClientAllocFree",
        "RpcSsSwapClientAllocFree",
        "IViewObject",
        # Appears twice for some reason
        "VerSetConditionMask",
        # We don't handle multi dimensional arrays correctly.
        "tagINPUT_TRANSFORM",
        "_CRYPT_AES_128_KEY_STATE",
        "_CRYPT_AES_256_KEY_STATE"
    ]
    for _, x in xs:
        if not is_linux:
            done = False
            for a in blck:
                if a in x:
                    done = True
                    break
            if done:
                continue
        output.write(x + "\n")

    print("\n".join(map(repr, tu.diagnostics)))


if __name__ == "__main__":
    main()
