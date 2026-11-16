# C++ Guidelines

Apply these rules when writing or reviewing C++ source code.

## Rules

- Do not use a type alias, `using` directive, abbreviation, or macro just to shorten code. A semantic alias such as
  `using UserId = int64_t;` is fine; `using namespace` is not.
- To avoid indeterminate order of initialization or destruction:
  - dynamic initialization is allowed only for function-local static variables;
  - non-local static variables must not be dynamically initialized or destroyed.
- Do not put a function implementation in a header if it has more than one statement. Templates are exempt: their
  definitions must be visible at every instantiation, so keep them in the header or an included definition file.
- Put implementation-detail symbols in the implementation file. If a member function never uses `this` or any member,
  turn it into a free function in the anonymous namespace of the implementation file.
- Use smart pointers to own memory. Raw pointers are fine for non-owning observation and C API boundaries.
- Use RAII to manage resources.

## Naming conventions

- If a function is only for testing, suffix the name with `ForTest`.
- When testing a single file rather than a module or subsystem, name the test file after the tested file with a `_test`
  suffix (for example `foo.cpp` -> `foo_test.cpp`) and put it in the same directory.
