# Data Directory

This project follows a medallion architecture:

```text
raw → bronze → silver → gold
```

Large data files should not be committed. Keep only `.gitkeep`, schemas, dictionaries, and small samples when necessary.
