""" Formatters from django DB to HTML structures. """
import itertools
import typing as ty

from django.core.paginator import EmptyPage, Page, Paginator
from django.shortcuts import reverse
from django.utils.safestring import mark_safe
from django.views.generic.base import ContextMixin

from .. import exceptions


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


class HtmlBase:
    def __init__(self, parent=None):
        self.parent = parent

    def html(self) -> str:
        return ""

    def __str__(self):
        return mark_safe(str(self.html()))


class Table(HtmlBase):
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
        try:
            self.page = self.paginator.page(page_num)
        except EmptyPage:
            raise exceptions.NotFound() from None
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

    class _Row(list):
        def __init__(self, row, item):
            super().__init__(row)
            self.item = item

    def rows(self) -> ty.Iterator[ty.List[str]]:
        """ Yields rows. """
        for item in self.objects:
            yield self._Row(
                (getattr(item, field.name) for field in self.model_fields), item
            )

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
            items.insert(0, a_icon.format(page.number - 1, "prev"))
        if page.has_next():
            items.append(a_icon.format(page.number + 1, "next"))
        return Flatter(
            '<div class="row centered"><p>', " ".join(items), "</p></div>", sep=""
        )

    def html(self):
        if self.objects:
            table = ['<table class="table">', self._head(), self._body(), "</table>"]
            if self.paginator:
                table.append(self.page_info())
            return Flatter(obj=table)
        else:
            return '<p style="align: center;">{}</p>'.format(str(self.empty_msg))


class Sidebar(HtmlBase):
    """ Nav element with the vertical sidebar """

    row = '<a class="nav-link nowrap %s" href="%s">%s</a>'

    def __init__(self, active_num: int, obj):
        self.active = active_num

    def items(self) -> ty.Iterable[ty.Tuple[str, str]]:
        return []

    def _items(self):
        for i, (url, name) in enumerate(self.items()):
            active = "active" if i == self.active else ""
            yield self.row % (active, url, name)

    def html(self):
        return Flatter(
            '<nav class="nav nav-tabs nav-sidetabs flex-column">',
            self._items(),
            "</nav>",
        )


class SidebarMixin(ContextMixin):
    """
    View mixin that provides sidebar object in the template context.
    """

    sidebar = Sidebar
    sidebar_active = 0
    entity_name = "object"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self._add_sidebar(context)
        return context

    def _add_sidebar(self, context):
        context["sidebar"] = self.sidebar(
            self.sidebar_active, getattr(self, self.entity_name)
        )


class DropdownButtons(HtmlBase):
    """ Button with other buttons in the dropdown menu. """

    def __init__(self, parent, button, contents: ty.Mapping, num=0):
        super().__init__(parent=parent)
        self.button = button
        self.contents = contents
        self.num = num
        self._group = f"button_grp_{self.num}"

    def _button(self):
        return "<button %s>%s</button>" % (
            ElementAttrs(
                {
                    "data-toggle": "dropdown",
                    "class": "btn btn-sm btn-outline-primary",
                    "button-secondary": "",
                    "dropdown-toggle": "",
                    "aria-haspopup": "true",
                    "aria-expanded": "false",
                },
                id="button_grp_%s" % self.num,
                type="button",
            ),
            self.button,
        )

    def _contents(self):
        return "".join(
            '<a class="dropdown-item" href="%s">%s</a>' % (link, name.capitalize())
            for name, link in self.contents.items()
        )

    def dropdown_menu(self):
        return '<div class="dropdown-menu" aria-labelledby="%s">%s</div>' % (
            self._group,
            self._contents(),
        )

    def html(self):
        return '<div class="btn-group">%s%s</div>' % (
            self._button(),
            self.dropdown_menu(),
        )


class ElementAttrs(dict):
    """
    Collection of HTML element attributes, such as id, class, etc.
    """

    def __init__(self, mapping=None, **kwargs):
        kwargs.update(mapping or {})
        super().__init__(**kwargs)

    def __str__(self):
        return " ".join('%s="%s"' % x for x in self.items())
