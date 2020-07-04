# YAXI

*Yet Another Xml Interface;* terse queries using slices and calls with no deps.

For cases when your XML documents keep changing with no regard for rhyme,
reason, or precedent, and you just want to pull out the right pieces of data.

## Installing

Requires python>=3.6.

```bash
pip install yaxi
```

Developers can install an editable copy using `flit install --symlink`.

## Examples

`yaxi.YaxElement` is just a subclass of builtin
`xml.etree.ElementTree.Element`, so the right hand side of the below examples
is just the equivalent `xml` module command:

```python
import xml
from yaxi import
>>> x['What'] == x.find('What')
True
>>> x['What']['Param':] == x.find('What').findall('Param')
True
>>> x['What']['Param':('name',):'FAR'] == \
...     [p for p in x.find('What').findall('Param')
...      if p.get('name') == 'FAR']
True
```

You can also combine multiple indexing operations into a single
attempt:

```python
>>> x['What', 'Param':('name',):'FAR', 0] == \
...     [p for p in x.find('What').findall('Param')
...      if p.get('name') == 'FAR'][0]
True
```

For inconsistent XML that might match one of multiple schemas, you can
``Attempt`` to get the data from multiple locations and only raise an error if
none of them work:

```python
>>> x.attempt['aefpqiefd', 2:, 0] \                     # will fail
...          ['What', 'Param':('name',):'FAR', 0] \     # 1st success, returned
...          ['Foejqnfd'].get() == \                    # ignored
...     [p for p in x.find('What').findall('Param')
...      if p.get('name') == 'FAR']
```
