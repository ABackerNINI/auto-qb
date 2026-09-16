> 版本: 0.19.1 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Perform round-trip YAML processing

Source: https://github.com/pycontribs/ruamel-yaml/blob/master/_autodocs/api-reference/YAML.md

Loads and dumps YAML while preserving comments and formatting.

```python
yaml = YAML()
data = yaml.load(open('input.yaml', 'rb'))
# Modify data...
yaml.dump(data, open('output.yaml', 'w'))
```

--------------------------------

### Preserve comments during modification

Source: https://github.com/pycontribs/ruamel-yaml/blob/master/_autodocs/api-reference/CommentedMap-CommentedSeq.md

Load and dump YAML data while modifying values to maintain existing comments.

```python
from ruamel.yaml import YAML

yaml = YAML()
data = yaml.load(open('config.yaml', 'rb'))

# Modify values - comments are preserved
data['timeout'] = 60
data['retries'] = 5

# Round-trip back to file
yaml.dump(data, open('config.yaml', 'w'))
```

--------------------------------

### Perform safe YAML loading

Source: https://github.com/pycontribs/ruamel-yaml/blob/master/_autodocs/api-reference/YAML.md

Loads YAML data without executing arbitrary code.

```python
yaml = YAML(typ='safe')
data = yaml.load(open('config.yaml', 'rb'))
```

--------------------------------

### Preserve quoting style

Source: https://github.com/pycontribs/ruamel-yaml/blob/master/_autodocs/api-reference/Scalars.md

Configure YAML instance to maintain original quote styles during round-trip.

```python
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True

# Load YAML
data = yaml.load("""
quoted: "value"
single: 'another'
plain: text
""")

# data['quoted'] is DoubleQuotedScalarString("value")
# data['single'] is SingleQuotedScalarString("another")
# data['plain'] is str("text")

# Dump - quoting style is preserved
yaml.dump(data, stream)
# Output:
# quoted: "value"
# single: 'another'
# plain: text
```

--------------------------------

### Configure Round-trip Preservation

Source: https://github.com/pycontribs/ruamel-yaml/blob/master/_autodocs/configuration.md

Sets configuration options to maximize the preservation of formatting and structure during round-trip processing.

```python
yaml = YAML()
yaml.preserve_quotes = True
yaml.explicit_start = True
yaml.explicit_end = True
yaml.version = (1, 2)
```