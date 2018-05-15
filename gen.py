#!/usr/bin/python

from clang.cindex import *

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

def parse_args():
    import sys
    in_clang_args = False
    clang_args = []
    dirs = []
    for arg in sys.argv[1:]:
        if arg == "--":
            in_clang_args = True
            continue

        if in_clang_args:
            clang_args.append(arg)
        else:
            dirs.append(arg)

    return (dirs, clang_args)

def create_dummy_file(dirs):
    import os

    with open("dummy.c", mode="w") as dummy:
        files = [f for d in dirs for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
        files = files + [os.path.join("/usr/include/", f) for f in std_files]

        for f in files:
            dummy.write("""#include "{}"\n""".format(f))

def get_decls(tu):
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

    def format_type(t, n = None, expand = False, resolve = False, in_typedef_resolve = False, print_struct_name = True):
        fmt = "{}{}".format("const " if t.is_const_qualified() else "", "volatile " if t.is_volatile_qualified() else "")
        n = " " + n if n != None and print_struct_name else ""
        c = t.get_declaration()
        if t.kind == TypeKind.ELABORATED and expand and c.displayname == "":
            #print(c.kind, c.type.kind, c.type.get_declaration().kind)
            t = c.type

        # wtf
        if t.kind == TypeKind.INT and n is not None and n == " size_t":
            return fmt + "size_t"

        tbl = {
            TypeKind.VOID            : lambda: "void",
            TypeKind.BOOL            : lambda: "bool",
            TypeKind.CHAR_U          : lambda: "char",
            TypeKind.UCHAR           : lambda: "unsigned char",
            TypeKind.USHORT          : lambda: "unsigned short",
            TypeKind.UINT            : lambda: "unsigned int",
            TypeKind.ULONG           : lambda: "unsigned long",
            TypeKind.ULONGLONG       : lambda: "unsigned long long",
            TypeKind.CHAR_S          : lambda: "char",
            TypeKind.SCHAR           : lambda: "signed char",
            TypeKind.SHORT           : lambda: "short",
            TypeKind.INT             : lambda: "int",
            TypeKind.LONG            : lambda: "long",
            TypeKind.LONGLONG        : lambda: "long long",
            TypeKind.FLOAT           : lambda: "float",
            TypeKind.DOUBLE          : lambda: "double",
            TypeKind.LONGDOUBLE      : lambda: "long double",
            TypeKind.ENUM            : lambda: "enum {}".format(t.spelling),
        }

        if t.kind == TypeKind.POINTER:
            pt = t.get_pointee()
            if pt.kind == TypeKind.FUNCTIONPROTO:
                return "{}(*{})({})".format(
                        format_type(pt.get_result(), expand=expand),
                        n,
                        ", ".join([format_type(t, expand=expand) for t in pt.argument_types()]))
            elif pt.kind == TypeKind.UNEXPOSED:
                return format_type(pt, expand=expand, n=n[1:])
            return format_type(t.get_pointee(), expand=expand) + "*" + \
                (" const" if t.is_const_qualified() else "") + \
                (" volatile" if t.is_volatile_qualified() else "") + \
                n
        elif t.kind == TypeKind.TYPEDEF and resolve:
            if t.get_canonical().kind == TypeKind.FUNCTIONPROTO:
                # Fuck gnu libc for using this feature
                return ""
            #print(t.get_declaration().get_definition().type.kind, t.get_declaration().underlying_typedef_type.displayname)
            return "typedef {};".format(format_type(t.get_declaration().underlying_typedef_type, n=t.get_typedef_name(), expand=True, in_typedef_resolve=True))
        elif t.kind == TypeKind.RECORD:
            ty = "struct"
            if t.get_declaration().kind == CursorKind.UNION_DECL:
                ty = "union"

            #if in_typedef_resolve and t.get_declaration().displayname != "":
            #    return "{} {}{}".format(ty, t.get_declaration().displayname, n)

            return "{}{}{{\n{}}}{}".format(
                    ty,
                    n if not in_typedef_resolve else (" " + t.get_declaration().displayname if in_typedef_resolve and t.get_declaration().displayname != "" else ""),
                    "".join([format_type(c.type, expand=expand, n=c.displayname, in_typedef_resolve = True) + ";\n" for c in t.get_fields()]),
                    n if in_typedef_resolve else "")
        elif t.kind == TypeKind.TYPEDEF:
            return fmt + t.get_typedef_name() + n
        elif t.kind == TypeKind.INCOMPLETEARRAY:
            return format_type(t.element_type, expand=expand, print_struct_name = False) + n + "[]"
        elif t.kind == TypeKind.CONSTANTARRAY:
            return format_type(t.element_type, expand=expand, print_struct_name = False) + n + "[{}]".format(t.element_count)
        elif t.kind == TypeKind.ELABORATED:
            return t.spelling + n
        elif t.kind in tbl:
            return fmt + tbl[t.kind]() + n
        elif t.kind == TypeKind.UNEXPOSED:
            s = t.spelling.split(" ")
            r = s[0] + "(*" + n + ")" + " ".join(s[1:])
            print("UNEXPOSED", t.spelling, "------- Patched", r)
            return r

        print("Not handled: ", t.kind, ": ", t.spelling)
        assert(False)

    def iter_children(t, sts):
        if t.kind == TypeKind.ELABORATED:
            t = t.get_declaration().type

        if t.kind == TypeKind.RECORD:
            decl = t.get_declaration()
            sts.append((-1, decl))
        elif t.kind == TypeKind.TYPEDEF:
            iter_children(t.get_canonical(), sts)

    assert(tu.cursor.kind.is_translation_unit())
    structs = []
    functions = []
    typedefs = []
    already = set()
    for i, c in enumerate(tu.cursor.get_children()):
        # TODO: first add all structs and typedefs and what not as well.
        # Then filter whether they're used (i.e. insert them with used=False
        # and use iter_children to set used to True).
        if c.kind == CursorKind.STRUCT_DECL:
            structs.append((i, c))
        elif c.kind == CursorKind.TYPEDEF_DECL:
            typedefs.append((i, c))
            iter_children(c.type, structs)
        if not (c.kind.is_declaration() and c.kind == CursorKind.FUNCTION_DECL):
            continue
        ft = c.type
        assert(ft.kind == TypeKind.FUNCTIONPROTO)
        if blocked(ft.get_result()):
            continue

        if c.displayname in already:
            continue
        already.add(c.displayname)

        args = []
        cont = False
        for p in c.get_arguments():
            assert(p.kind == CursorKind.PARM_DECL)
            a = p.type
            if blocked(a):
                cont = True
                break

            args.append(format_type(a, n=p.mangled_name))

        if cont:
            continue

        ret_type = format_type(ft.get_result())

        functions.append(
            (i, "{} {}({});".format(ret_type, c.mangled_name, ",".join(args)))
        )

    # Expand typedefs and add references to structs.
    tds = []
    block = [
        "int8_t", "uint8_t", "int16_t", "uint16_t", "int32_t", "uint32_t", "size_t", "uintptr_t", "intptr_t", "offset_t",
        "int64_t", "uint64_t", "ssize_t",
        # Remove these once bn can do "typedef (struct|union) a a;"
        "ucontext_t", "_IO_FILE", "pthread_attr_t",
    ]
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
        if tdn in already:
            continue
        already.add(tdn)
        tds.append((i, format_type(td.type, resolve=True)))

    strcts = []
    already = set()
    replace = {
        "_IO_FILE": "struct _IO_FILE { void* __unused; };",
        "ucontext_t": "struct ucontext_t { void* __unused; };",
        "_IO_jump_t": "struct _IO_jump_t { void* __unused; };",
        "_IO_FILE_plus": "struct _IO_FILE_plus { void* __unused; };",
    }
    for i, st in structs:
        if st.displayname == "":
            continue
        if st.displayname in already:
            continue
        if st.displayname in replace:
            strcts.append((i, replace[st.displayname]))
            already.add(st.displayname)
            continue
        already.add(st.displayname)
        strcts.append((i, format_type(st.type, n=st.displayname, expand=True) + ";"))


    return functions, strcts, tds

def main():
    dirs, clang_args = parse_args()
    create_dummy_file(dirs)

    index = Index.create()
    tu = index.parse("dummy.c", args=clang_args)

    with open("posix.c", "w") as output:
        fns, structs, typedefs = get_decls(tu)
        # TODO: build tree and return it so that we can print them in proper order
        xs = sorted(fns + structs + typedefs, key=lambda i: i[0])
        output.write("struct __locale_data { void* __unused; };\n")
        for _, x in xs:
            output.write(x + "\n")

if __name__ == "__main__":
    main()

