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

    def format_type(t, n = None, resolve_typedefs = False, in_typedef_resolve = False, c =None):
        fmt = "{}{}".format("const " if t.is_const_qualified() else "", "volatile " if t.is_volatile_qualified() else "")
        n = " " + n if n != None else ""
        tbl = {
            TypeKind.VOID       : lambda: "void",
            TypeKind.BOOL       : lambda: "bool",
            TypeKind.CHAR_U     : lambda: "char",
            TypeKind.UCHAR      : lambda: "unsigned char",
            TypeKind.USHORT     : lambda: "unsigned short",
            TypeKind.UINT       : lambda: "unsigned int",
            TypeKind.ULONG      : lambda: "unsigned long",
            TypeKind.ULONGLONG  : lambda: "unsigned long long",
            TypeKind.CHAR_S     : lambda: "char",
            TypeKind.SCHAR      : lambda: "signed char",
            TypeKind.SHORT      : lambda: "short",
            TypeKind.INT        : lambda: "int",
            TypeKind.LONG       : lambda: "long",
            TypeKind.LONGLONG   : lambda: "long long",
            TypeKind.FLOAT      : lambda: "float",
            TypeKind.DOUBLE     : lambda: "double",
            TypeKind.LONGDOUBLE : lambda: "long double",
            TypeKind.ENUM       : lambda: "enum {}".format(t.spelling),
        }

        if t.kind == TypeKind.POINTER:
            # Special case
            # TODO: function pointers
            return format_type(t.get_pointee()) + "*" + \
                (" const" if t.is_const_qualified() else "") + \
                (" volatile" if t.is_volatile_qualified() else "") + \
                n
        elif t.kind == TypeKind.CONSTANTARRAY:
            return format_type(t.element_type) + n + "[{}]".format(t.element_count)
        elif t.kind == TypeKind.TYPEDEF and resolve_typedefs:
            return "typedef {};".format(format_type(t.get_canonical(), n=t.get_typedef_name(), in_typedef_resolve=True))
        elif t.kind in tbl:
            return fmt + tbl[t.kind]() + n
        elif t.kind == TypeKind.RECORD or (c is not None and c.kind == CursorKind.FIELD_DECL and c.type.get_declaration().type == TypeKind.RECORD):
            ty = "struct"
            rt = None
            if c is not None and c.kind == CursorKind.FIELD_DECL:
                rt = c.type.get_declaration().type
                if rt.kind == CursorKind.UNION_DECL:
                    ty = "union"
            if rt is not None:
                print(rt.kind)
                t = rt
                in_typedef_resolve = True
            return "{}{}{{\n{}}}{}".format(
                    ty,
                    n if not in_typedef_resolve else "",
                    "".join([format_type(c.type, n=c.displayname, c=c) + ";\n" for c in t.get_fields()]),
                    n if in_typedef_resolve else "")

        return t.spelling + n

    def iter_children(t, tds, sts):
        if t.kind == TypeKind.RECORD and t.get_declaration() not in sts:
            sts.append(t.get_declaration())
            for c in t.get_fields():
                iter_children(c, tds, sts)
        elif t.kind == TypeKind.TYPEDEF and t not in tds:
            tds.append(t)
            iter_children(t.get_canonical(), tds, sts)
        elif t.kind == TypeKind.POINTER:
            iter_children(base_type(t), tds, sts)
        elif t.kind == TypeKind.FUNCTIONPROTO:
            iter_children(t.get_result(), tds, sts)
            for a in t.argument_types():
                iter_children(a, tds, sts)

    assert(tu.cursor.kind.is_translation_unit())
    structs = []
    functions = []
    typedefs = []
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
    for td in typedefs:
        rt = td.get_canonical()
        bt = base_type(rt)
        if rt.kind == TypeKind.POINTER and bt.kind == TypeKind.FUNCTIONPROTO:
            tds.append("typedef {}(*{})({});".format(
                format_type(bt.get_result()),
                td.get_typedef_name(),
                ", ".join([format_type(t) for t in bt.argument_types()])
            ))
        else:
            #tds.append("typedef {} {};".format(format_type(rt), td.get_typedef_name()))
            tds.append(format_type(td, resolve_typedefs=True))

    strcts = []
    for st in structs:
        if st.displayname != "":
            strcts.append(format_type(st.type, n=st.displayname) + ";")


    return functions, strcts, tds

def main():
    dirs, clang_args = parse_args()
    create_dummy_file(dirs)

    index = Index.create()
    tu = index.parse("dummy.c", args=clang_args)

    with open("posix.c", "w") as output:
        fns, structs, typedefs = get_decls(tu)
        xs = [structs, typedefs, fns]
        for x in xs:
            for a in x:
                output.write(a + "\n")
            output.write("\n\n")


if __name__ == "__main__":
    main()

