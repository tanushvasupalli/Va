## 2023-10-24 - Optimizing Python os.walk traversal depth
**Learning:** In Python, the `os.walk` generator recursively explores directories. Simply calling `continue` when a depth limit is reached only skips processing the files in the directory; `os.walk` will still traverse into all subdirectories, wasting massive I/O.
**Action:** Always modify the `dirs` list in-place (e.g., `dirs[:] = []`) to prevent `os.walk` from descending into directories that are beyond the target depth limit.
