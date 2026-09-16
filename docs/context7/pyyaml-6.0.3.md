> 版本: 6.0.3 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Load, Dump, and Define Custom Types with PyYAML

Source: https://github.com/yaml/pyyaml/blob/main/_autodocs/00-START-HERE.md

Demonstrates basic YAML loading and dumping using safe_load and safe_dump. Also shows how to define a custom YAML type with YAMLObject for automatic serialization and deserialization.

```python
import yaml

# Load YAML (safe for untrusted input)
data = yaml.safe_load("key: value")

# Dump to YAML
yaml_str = yaml.safe_dump({'key': 'value'})

# Define custom YAML type
class Point(yaml.YAMLObject):
    yaml_tag = '!point'
    def __init__(self, x, y):
        self.x = x
        self.y = y

# That's it — automatic serialization/deserialization

```

--------------------------------

### Load all YAML documents with SafeLoader

Source: https://github.com/yaml/pyyaml/blob/main/_autodocs/api-reference/top-level-functions.md

Parses all YAML documents from a stream using `SafeLoader`. This function returns an iterator yielding Python objects for each document and is recommended for untrusted input as it only constructs simple Python objects.

```python
import yaml

yaml_str = """---
item1: value1
---
item2: value2
"""

for doc in yaml.load_all(yaml_str, Loader=yaml.SafeLoader):
    print(doc)
```

--------------------------------

### Dumping Python Data to YAML String or File

Source: https://github.com/yaml/pyyaml/blob/main/_autodocs/00-START-HERE.md

Use yaml.safe_dump() to serialize Python data structures into YAML. Options like default_flow_style, sort_keys, and width can customize the output.

```python
import yaml

# Dump to string
yaml_str = yaml.safe_dump(data)

# Dump with options
yaml_str = yaml.safe_dump(
    data,
    default_flow_style=False,  # Pretty format
    sort_keys=True,             # Sort keys
    width=100                   # Line width
)

# Dump to file
with open('output.yaml', 'w') as f:
    yaml.safe_dump(data, f)
```

--------------------------------

### SafeLoader

Source: https://github.com/yaml/pyyaml/blob/main/_autodocs/api-reference/loaders.md

The safest loader for untrusted YAML. It only constructs simple Python objects (dicts, lists, strings, numbers, booleans, null) and is recommended for all production use with external input.

```APIDOC
## SafeLoader

### Description
The safest loader for untrusted YAML. Only constructs simple Python objects (dicts, lists, strings, numbers, booleans, null). Recommended for all production use with external input.

### Constructor

```python
SafeLoader(stream)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| stream | str, bytes, or file-like | Yes | — | YAML input stream |

### Methods

Same as `BaseLoader`.

### Example

```python
import yaml

yaml_content = "message: hello\ncount: 42"
loader = yaml.SafeLoader(yaml_content)
try:
    data = loader.get_single_data()
    assert isinstance(data, dict)
    assert data['message'] == 'hello'
finally:
    loader.dispose()
```
```

--------------------------------

### load_all()

Source: https://github.com/yaml/pyyaml/blob/main/_autodocs/api-reference/top-level-functions.md

Parses all YAML documents within a stream and yields corresponding Python objects. Requires explicit Loader specification.

```APIDOC
## load_all()

### Description
Parse all YAML documents in a stream and produce corresponding Python objects.

### Signature
```python
load_all(stream, Loader) -> Iterator[Any]
```

### Parameters
#### Path Parameters
- **stream** (str, bytes, or file-like) - Required - Input YAML stream
- **Loader** (Loader class) - Required - Loader class to use. Must be explicitly specified.

### Returns
Iterator yielding Python objects for each document.

### Example
```python
import yaml

yaml_str = """---
item1: value1
---
item2: value2
"""

for doc in yaml.load_all(yaml_str, Loader=yaml.SafeLoader):
    print(doc)
```
```