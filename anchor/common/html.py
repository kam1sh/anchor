""" Formatters from django DB to HTML structures. """
import itertools
import typing as ty

from django.core.paginator import Paginator, Page
from django.shortcuts import reverse
from django.utils.safestring import mark_safe

__all__ = ["Table", "RowFormatter"]


def tag(tag, obj):
    return [f"<{tag}>", obj, f"</{tag}>"]


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
            if isinstance(item, str):
                yield item
            elif hasattr(item, "__iter__"):
                yield from Flatter(obj=item)
            else:
                yield str(item)

    def __str__(self):
        return self.sep.join(self)


class Table:
    """
    Formatter that renders ResultSet
    as a Bootstrap table.

    Attributes:
    - Fields: List of entity field names to include,
      could be set as class variable and/or could be overriden in __init__.
    """

    fields: ty.List[str] = []
    empty_msg = "There is no items available yet."
    reverse_link: ty.Optional[ty.Callable] = None

    paginator: Paginator = None
    page: Page = None
    size: int = 20

    def __init__(self, value, fields: ty.List[str] = None, request=None, paginate=True):
        if value is None:
            raise ValueError("'value' could not be None")
        self.request = request
        self.objects = self._build_page(value) if paginate else value
        self.model = value.model
        self.model_fields = self.model._meta.fields
        fields = fields or self.fields
        if fields:
            self.model_fields = [x for x in self.model_fields if x.name in fields]
            # workaround for mypy's Item "None" of "Optional[List[str]]"
            # has no attribute "index"
            data = fields
            self.model_fields.sort(key=lambda x: data.index(x.name))

    def _build_page(self, objects):
        request = self.request.GET if self.request else {}
        page_num, self.size = request.get("page", 1), request.get("size", 20)
        if not objects.ordered:
            objects = objects.order_by("id")
        self.paginator = Paginator(objects, per_page=self.size)
        self.page = self.paginator.page(page_num)
        return self.page

    def head(self) -> ty.Iterator[str]:
        """ Column names. """
        for field in self.model_fields:
            yield field.verbose_name.capitalize()

    def _head(self) -> ty.Iterable:
        yield "<thead>"
        for row in self.head():
            yield tag("th", row)
        yield "</thead>"

    def rows(self) -> ty.Iterator[ty.List[str]]:
        """ Yields rows. """
        for item in self.objects:
            yield [getattr(item, field.name) for field in self.model_fields]

    def _body(self) -> ty.Iterable:
        yield "<tbody>"
        for row in self.rows():
            yield "<tr>", map("<td>{}</td>".format, row), "</tr>"
        yield "</tbody>"

    def _get_reverse(self):
        if not (self.reverse_link or self.request):
            raise ValueError(
                "Provide 'reverse_link' method or pass request in __init__."
            )
        if self.reverse_link:
            return self.reverse_link()  # pylint: disable=not-callable
        return self.request.path

    def page_info(self) -> Flatter:
        page = self.page
        items = ["page {} of {}".format(page.number, self.paginator.num_pages)]
        a_icon = '<a href="%s?page={}">{}</a>' % self._get_reverse()
        if page.has_previous():
            items.insert(0, a_icon.format(page.number, "prev"))
        if page.has_next():
            items.append(a_icon.format(page.number, "next"))
        return Flatter('<div class="row centered">', items, "</div>", sep="")

    def __str__(self):
        if self.objects:
            table = ['<table class="table">', self._head(), self._body(), "</table>"]
            if self.paginator:
                table.append(self.page_info())
            out = str(Flatter(obj=table))
        else:
            out = '<p style="align: center;">{}</p>'.format(str(self.empty_msg))
        return mark_safe(out)


class PageInfo:
    def __init__(self, page):
        self.page = page

    def __str__(self):
        return Flatter("<p>", "</p>")


class RowFormatter:
    def __init__(self, item, fields: ty.Iterable[str]):
        self.item = item
        self.fields = fields

    def cols(self) -> list:
        return [getattr(self.item, f) for f in self.fields]

    def __str__(self):
        return ("<tr>", self.cols(), "<tr>")
