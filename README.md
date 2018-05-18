Usage:
```
./gen.py -- <clang command line options here>
```
Will create a file named `posix.c` from the C standard library and linux specific functions, containing structure, enum and function declarations. It can be either placed in `binaryninja/types/posix.c` so that it is loaded on startup, or can be manually loaded with this script:

```python
stuff = bv.platform.parse_types_from_source_file("path/to/posix.c")

for name, t in stuff.types.items():
    bv.define_type(Type.generate_auto_type_id("source", name), name, t)

for fn in bv.functions:
	  if fn.name in stuff.functions:
		    fn.set_user_type(stuff.functions[fn.name])
```

