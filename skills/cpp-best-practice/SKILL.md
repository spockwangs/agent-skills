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
