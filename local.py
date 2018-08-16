def un_dll_name(x):
    if "!" in x and "@IAT" in x:
        return x[x.find("!") + 1 : x.find("@IAT")]
    elif "!" in x:
        return x[x.find("!") + 1:]
    return x

def load_stuff(platform, type_imports=False):
    stuff = bv.platform.parse_types_from_source_file( "/vm/Programming/Python/cgen/{}.c".format(platform))
    for name, t in stuff.types.items():
        bv.define_type(Type.generate_auto_type_id("source", name), name, t)
    fns = bv.functions + [bv.get_function_at(s.address) for s in bv.get_symbols_of_type(SymbolType.ImportedFunctionSymbol)]
    for fn in fns:
        f_name = un_dll_name(fn.name)
        if f_name in stuff.functions:
            fn.set_user_type(stuff.functions[f_name])
    if platform == "windows" or type_imports:
        # Many times IAT things will get called directly.
        for symbol in bv.get_symbols_of_type(SymbolType.ImportAddressSymbol):
            s_name = un_dll_name(symbol.name)
            if s_name in stuff.functions:
                p = Type.pointer(bv.arch, stuff.functions[s_name], const=True)
                bv.define_user_data_var(symbol.address, p)

