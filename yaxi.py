"Yet Another Xml Interface; terse queries using slices and calls with no deps."

__version__ = '0.2.0'

from typing import List, Dict, Tuple, Any
from xml.etree.ElementTree import Element, fromstring as fromstr


class YaxElement(Element):
    """
    Initialize from an ``xml.etree.ElementTree.Element. For example, load from
    string using ``YaxElement(xml.etree.ElementTree.fromstring(...))`` or from
    file with ``YaxElement(xml.etree.ElementTree.parse(...).getroot())``.
    Provides a ``fromstring`` method for the former case and ``from_json``
    and ``to_json`` methods for serializing as JSON-compatible dicts (in cases
    where that's needed).
    """

    def __init__(self, el: Element):
        "Init from an ``Element``."
        if not isinstance(el, Element):
            raise ValueError("Must initialize from an xml.etree.ElementTree.Element,"
                             " not %s"%el)
        super().__init__(el.tag, el.attrib)
        self.text = el.text
        for c in el:
            self.append(c)

    def __call__(self, idx):
        "Alias for ``get()``."
        res = self.get(idx)
        if res is None:
            raise IndexError(f"No such attribute: {idx}")
        return res

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
        True

        You can also combine multiple indexing operations into a single
        attempt:
        >>> x['What', 'Param':('name',):'FAR', 0] == \
        ...     [p for p in x.find('What').findall('Param')
        ...      if p.get('name') == 'FAR'][0]
        True
        """
        res = self._getitem_noerr_(idx)
        return res
        # if res is None:
        #     raise IndexError(f"Failed query: {idx}")
        # return YaxElement(res)

    @staticmethod
    def _cast_and_err_(res, idx):
        if res is None:
            raise IndexError(f"Failed query: {idx}")
        return YaxElement(res)

    def _getitem_noerr_(self, idx):
        if isinstance(idx, tuple):
            res = self
            get = type(self)._getitem_noerr_
            for i in idx:
                if isinstance(res, Element):
                    res = get(res, i)
                else:
                    res = res[i]
            return res
        if isinstance(idx, slice) and isinstance(idx.start, str):
            res = self.findall(idx.start)
            if (isinstance(idx.stop, tuple) and
                    all(isinstance(i, str) for i in idx.stop)):
                q = idx.step if isinstance(idx.step, tuple) else (idx.step,)
                return [YaxElement(r) for r in res
                        if any(r.get(i) == j
                               for i in idx.stop for j in q)]
            return [YaxElement(r) for r in res[:idx.stop:idx.step]]
        if isinstance(idx, str):
            return self._cast_and_err_(self.find(idx), idx)
        return self._cast_and_err_(super().__getitem__(idx), idx)

    @property
    def attempt(self):
        return Attempt(self)

    @classmethod
    def fromstring(cls, string: str):
        return cls(fromstr(string))

    def to_json(self) -> Tuple[str, str, Dict[str, Any], List[tuple]]:
        return (self.tag, self.text, self.attrib, [c.to_json() for c in self])

    @classmethod
    def from_json(cls, json: Tuple[str, str, Dict[str, Any], List[tuple]]):
        tag, text, attrib, children = json
        new = cls(Element(tag, attrib))
        if text is not None:
            setattr(new, 'text', text)
        for c in children:
            new.append(cls.from_json(c))
        return new


class Attempt:
    """
    Sometimes your XML files change quickly and without documentation.
    Try multiple queries in a row, returning the first successful one and only
    raising an error if they all fail, with an ``Attempt``. Call the
    ``Attempt`` instance to get the result or raise and error if none was
    found. Note that ``Attempts`` are transient, stateful objects meant to get
    a result and be discarded; use a ``StoredAttempt`` if you want persistence.
    """

    def __init__(self, el: YaxElement):
        self.el = el
        self.val = None
        self.err = None

    @property
    def text(self):
        self.val = self.val.text
        return self

    def __repr__(self):
        return (f'<{type(self).__name__}, el={self.el}, val={self.val}, '
                f'err={self.err}>')

    def __call__(self):
        if self.val is None:
            return self.el
        return self.val

    def __getitem__(self, idx):
        if self.val is None:
            try:
                self.val = self.el[idx]
            except IndexError as e:
                self.err = e
        return self


class StoredAttempt:
    """
    A casting validator/descriptor.
    """

    def __init__(self, outtype=None, queries=(), attrib=None, text=False,
                 cast=None):
        self.outtype = outtype
        self.queries = queries
        self.attrib = attrib
        self.gettext = text
        self.cast = cast or outtype

    def __call__(self, attribname):
        if self.gettext:
            raise IndexError("Inner text does not have attributes.")
        return type(self)(self.outtype, self.queries, attribname,
                          cast=self.cast)

    def __getitem__(self, query):
        if self.attrib is not None:
            raise IndexError("Attributes do not contain children.")
        if self.gettext:
            raise IndexError("Inner text does not contain children.")
        return type(self)(self.outtype, self.queries+(query,),
                          cast=self.cast)

    @property
    def text(self):
        if self.attrib is not None:
            raise IndexError("Attributes do not contain inner text.")
        return type(self)(self.outtype, self.queries, text=True,
                          cast=self.cast)

    @staticmethod
    def _qrepr(query):
        query = [*query] if isinstance(query, tuple) else [query]
        q = ', '.join(':'.join('' if s is None else repr(s)
                              for s in (q.start, q.stop, q.step))
                      if isinstance(q, slice) else repr(q) for q in query)
        return f'[{q}]'

    def __get__(self, obj):
        a = obj.attempt
        for query in self.queries:
            a = a[query]
        res = a()
        if self.attrib is not None:
            res = YaxElement.__call__(res, self.attrib)
        elif self.gettext:
            res = res.text
        if self.outtype is not None:
            res = self.cast(res)
        return res

    get = __get__

    def __repr__(self):
        return f'{type(self).__name__}({self.outtype})' \
            + ''.join(self._qrepr(q) for q in self.queries) \
            + f'({self.attrib or ""})'

    __str__ = __repr__


class YaxModelMeta(type):

    def __new__(cls, classname, bases, class_dict):
        new = super().__new__(cls, classname, bases, class_dict)
        if hasattr(new, '__annotations__'):
            new_validators = {k: v for k, v in new.__annotations__.items()
                              if isinstance(v, StoredAttempt)}
            for k, v in new_validators.items():
                new.__annotations__[k] = v.outtype
            new_validators.update(getattr(new, '__yaxi_validators__', {}))
            if new_validators:
                setattr(new, '__yaxi_validators__', new_validators)
        return new


class YaxModel(YaxElement, metaclass=YaxModelMeta):

    def __init__(self, el: Element):
        super().__init__(el)
        for k, v in getattr(self, '__yaxi_validators__', {}).items():
            setattr(self, k, v.get(self))
