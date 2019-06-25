""" Formatters from django DB to HTML structures. """
import itertools
import typing as ty

from django.utils.safestring import mark_safe

__all__ = ["Table", "RowFormatter"]


class Flatter:
    """
    Iterator that flatters nested iterators.
    >>> f = Flatter(["a", [1, 2, 3], "b", "cd", [4, [5], 6]])
    >>> list(f)
    ["a", 1, 2, 3, "b", "cd", 4, 5, 6]
    """

    def __init__(self, *items, obj=None, sep="\n"):
        self._items = obj or items
        self.sep = sep

    def __iter__(self):
        for item in self._items:
            if isinstance(item, ty.Iterable) and not isinstance(item, str):
                yield from Flatter(obj=item)
            else:
                yield item

    def __str__(self):
        return self.sep.join(self)


class Table:
    """
    Formatter that renders ResultSet
    as a Bootstrap table.
    """

    def __init__(self, value, fields: ty.List[str] = None):
        self.objects = value
        self.model = value.model
        self.fields = self.model._meta.fields
        if fields:
            self.fields = [x for x in self.fields if x.name in fields]
            # workaround for mypy's Item "None" of "Optional[List[str]]"
            # has no attribute "index"
            data = fields
            self.fields.sort(key=lambda x: data.index(x.name))

    def head(self) -> ty.Iterator[str]:
        for field in self.fields:
            yield field.verbose_name.capitalize()

    def _head(self) -> ty.Iterable:
        for row in self.head():
            yield "<th>{}</th>".format(row)

    def rows(self) -> ty.Iterator[ty.List[str]]:
        """ Returns iterator of rows """
        for item in self.objects:
            yield [getattr(item, field.name) for field in self.fields]

    def _body(self) -> ty.Iterable:
        for row in self.rows():
            yield "<tr>", map("<td>{}</td>".format, row), "</tr>"

    def __str__(self):
        head = ["<thead>", self._head(), "</thead>"]
        body = ["<tbody>", self._body(), "</tbody>"]
        return mark_safe(str(Flatter('<table class="table">', head, body, "</table>")))


class RowFormatter:
    def __init__(self, item, fields: ty.Iterable[str]):
        self.item = item
        self.fields = fields

    def cols(self) -> list:
        return [getattr(self.item, f) for f in self.fields]

    def __str__(self):
        return Flatter("<tr>", self.cols(), "<tr>")
