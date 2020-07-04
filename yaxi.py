"Yet Another Xml Interface; terse queries using slices and calls with no deps."

__version__ = '0.1.0'

from typing import List, Dict, Tuple, Any
from xml.etree.ElementTree import Element, fromstring


class XmlDict(Element):
    """
    Initialize from an ``xml.etree.ElementTree.Element. For example, load using
    ``XmlDict(xml.etree.ElementTree.fromstring(...))`` or from the root element
    of a file with ``XmlDict(xml.etree.ElementTree.parse(...).getroot())``.
    Provides a ``fromstring`` method for the former case and ``from_json``
    and ``to_json`` methods for serializing as JSON-compatible dicts.
    """

    def __init__(self, el: Element):
        "Init from an ``Element``."
        if not isinstance(el, Element):
            raise ValueError("Must initialize from an xml.etree.ElementTree.Element,"
                             " not %s"%el)
        super().__init__(el.tag, el.attrib)
        for c in el:
            self.append(type(self)(c))

    def __call__(self, idx):
        "Alias for ``get()``."
        return self.get(idx)

    def __getitem__(self, idx):
        """
        Provides a terser way to apply ``find`` and ``findall`` with simple
        filters on equality of attribute values. Queries can be provided all at
        once, allowing you to store multiple queries and try all of them.

        Examples
        --------
        >>> x['What'] == x.find('What')
        True
        >>> x['What']['Param':] == x.find('What').findall('Param')
        True
        >>> x['What']['Param':('name',):'FAR'] == \
        ...     [p for p in x.find('What').findall('Param')
        ...      if p.get('name') == 'FAR']

        You can also combine multiple indexing operations into a single
        attempt:
        >>> x['What', 'Param':('name',):'FAR', 0] == \
        ...     [p for p in x.find('What').findall('Param')
        ...      if p.get('name') == 'FAR'][0]
        """
        if isinstance(idx, tuple):
            res = self
            for i in idx:
                res = res[i]
            return res
        if isinstance(idx, slice) and isinstance(idx.start, str):
            res = self.findall(idx.start)
            if (isinstance(idx.stop, tuple) and
                    all(isinstance(i, str) for i in idx.stop)):
                return [r for r in res
                        if any(r.get(i) == idx.step for i in idx.stop)]
            return res[:idx.stop:idx.step]
        if isinstance(idx, str):
            return self.find(idx)
        return super().__getitem__(idx)

    @property
    def attempt(self):
        return Attempt(self)

    @classmethod
    def fromstring(cls, string: str):
        return cls(fromstring(str))

    def to_json(self) -> Tuple[str, Dict[str, Any], List[tuple]]:
        return (self.tag, self.attrib, [c.to_json() for c in self])

    @classmethod
    def from_json(cls, json: Tuple[str, Dict[str, Any], List[tuple]]):
        tag, attrib, children = json
        new = cls(Element(tag, attrib))
        for c in children:
            new.append(cls.from_json(c))
        return new


class Attempt:
    """
    Sometimes your XML files change quickly and without documentation.
    Try multiple queries in a row, returning the first successful one and only
    raising an error if they all fail, with an ``Attempt``. Call the
    ``Attempt`` instance to get the result or raise and error if none was
    found.
    """

    def __init__(self, el: XmlDict):
        self.el = el
        self.val = None
        self.err = None

    def __call__(self):
        if self.val is None:
            raise self.err or ValueError("No query run.")
        return self.val

    def __getitem__(self, idx):
        if self.val is None:
            try:
                self.val = self.el[idx]
            except IndexError as e:
                self.err = e
        return self
