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
        if t.kind == TypeKind.ELABORATED and expand:
            #print(c.kind, c.type.kind, c.type.get_declaration().kind)
            t = c.type

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
            return "typedef {};".format(format_type(t.get_canonical(), n=t.get_typedef_name(), expand=True, in_typedef_resolve=True))
        elif t.kind == TypeKind.RECORD:
            ty = "struct"
            if t.get_declaration().kind == CursorKind.UNION_DECL:
                ty = "union"
            #if c is not None and c.displayname != "" and in_typedef_resolve:
            #    return "{}{}{}".format(ty, c.displayname, n)
            #if not resolve:
            #    return "{} {}{}".format(ty, c.displayname, n)

            return "{}{}{{\n{}}}{}".format(
                    ty,
                    n if not in_typedef_resolve else "",
                    "".join([format_type(c.type, expand=expand, n=c.displayname) + ";\n" for c in t.get_fields()]),
                    n if in_typedef_resolve else "")
        elif t.kind == TypeKind.TYPEDEF:
            return fmt + t.get_typedef_name() + n
        elif t.kind == TypeKind.INCOMPLETEARRAY:
            return format_type(t.element_type, expand=expand, print_struct_name = False) + n + "[]"
        elif t.kind == TypeKind.CONSTANTARRAY:
            return format_type(t.element_type, expand=expand, print_struct_name = False) + n + "[{}]".format(t.element_count)
        elif t.kind == TypeKind.ELABORATED:
            print("ELABORATED: ", t.spelling)
            return t.spelling
        elif t.kind in tbl:
            return fmt + tbl[t.kind]() + n
        elif t.kind == TypeKind.UNEXPOSED:
            s = t.spelling.split(" ")
            r = s[0] + "(*" + n + ")" + " ".join(s[1:])
            print("UNEXPOSED", t.spelling, "------- Patched", r)
            return r

        print("Not handled: ", t.kind, ": ", t.spelling)
        assert(False)

    def iter_children(t, tds, sts):
        if t.kind == TypeKind.ELABORATED:
            t = t.get_declaration().type

        if t.kind == TypeKind.RECORD:
            decl = t.get_declaration()
            if decl.displayname != "" and decl.displayname not in sts:
                sts[decl.displayname] = decl
            for c in t.get_fields():
                iter_children(c.type, tds, sts)
        elif t.kind == TypeKind.TYPEDEF and t.get_typedef_name() not in tds:
            tds[t.get_typedef_name()] = t
            iter_children(t.get_canonical(), tds, sts)
        elif t.kind == TypeKind.POINTER:
            iter_children(base_type(t), tds, sts)
        elif t.kind == TypeKind.FUNCTIONPROTO:
            iter_children(t.get_result(), tds, sts)
            for a in t.argument_types():
                iter_children(a, tds, sts)

    assert(tu.cursor.kind.is_translation_unit())
    structs = {}
    functions = []
    typedefs = {}
    for c in tu.cursor.get_children():
        if not (c.kind.is_declaration() and c.kind == CursorKind.FUNCTION_DECL):
            continue
        ft = c.type
        assert(ft.kind == TypeKind.FUNCTIONPROTO)
        if blocked(ft.get_result()):
            continue

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

        iter_children(ft, typedefs, structs)

        ret_type = format_type(ft.get_result())

        functions.append(
            "{} {}({});".format(ret_type, c.mangled_name, ",".join(args))
        )

    # Expand typedefs and add references to structs.
    tds = []
    for _, td in typedefs.items():
        # TODO: if the typedef is something like "typdef struct a b;" then don't expand the struct!
        tds.append(format_type(td, resolve=True))

    strcts = []
    for _, st in structs.items():
        if st.displayname != "":
            strcts.append(format_type(st.type, n=st.displayname, expand=True) + ";")


    return functions, strcts, tds

def main():
    dirs, clang_args = parse_args()
    create_dummy_file(dirs)

    index = Index.create()
    tu = index.parse("dummy.c", args=clang_args)

    with open("posix.c", "w") as output:
        fns, structs, typedefs = get_decls(tu)
        # TODO: build tree and return it so that we can print them in proper order
        xs = [structs, typedefs, fns]
        for x in xs:
            for a in x:
                output.write(a + "\n")
            output.write("\n\n")


if __name__ == "__main__":
    main()

