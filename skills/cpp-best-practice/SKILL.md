---
name: cpp-best-practice
description: C++ best practice. Use when editing C++ files.
paths: ["**/*.h", "**/*.cpp", "**/*.hpp"]
user-invocable: false
---

Apply the following rules when editing C++ codes.

- Do not use type alias, `using` directive, abriavations, macros just to shorten codes.
- To avoid indeterminate order of initialization or destruction,
  - dynamic initialization is only allowed in static function scope variables.
  - dynamic destruction is disallowed totally.
- Do not inline functions if the function has more than one statement.
- If a function is only for testing suffix the name with `ForTest`.
- If testing a file instead of a module or subsystem the test file should be named as the tested file with suffix
  `_test` and put in the same directory.
- If a symbol belongs to implementation detail put it in the implementation file. If a function does not access any
  member of a class, put it in the anonymous namespace of the implementation file.
