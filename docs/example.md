# Example Documentation

This is an example documentation file.

## Usage

You can organize your docs in subdirectories:

```
docs/
├── INDEX.md          # Returned when load_docs() called with no args
├── getting-started.md
├── api/
│   ├── endpoints.md
│   └── auth.md
└── guides/
    └── deployment.md
```

Access nested docs with: `load_docs("api/endpoints")` or `load_docs("api/endpoints.md")`
