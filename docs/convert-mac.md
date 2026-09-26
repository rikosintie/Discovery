# Convert MAC addresses

This simple script takes 1 argument, a MAC address in any of the following formats and returns it in all of the formats.

- 64:e8:81:43:cc:4e
- 64e881-43cc4e
- 64e8.8143.cc4e
- 64-e8-81-43-cc-4e
- 64e88143cc4e

```bash
python3 convert-mac.py --mac 64:e8:81:43:cc:4e
64:e8:81:43:cc:4e
64e881-43cc4e
64e8.8143.cc4e
64-e8-81-43-cc-4e
64e88143cc4e
```
