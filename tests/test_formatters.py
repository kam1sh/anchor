"""
Tests for HTML formatters.
"""
import bs4
import pytest

from anchor.common import html
from anchor.users.models import User


def test_flatter_simple():
    f = html.Flatter([1, 2, 3])
    assert list(f) == ["1", "2", "3"]


def test_flatter_nested():
    f = html.Flatter(["a", [1, 2, 3], "b", "cd", [4, [5], 6]])
    assert list(f) == "a 1 2 3 b cd 4 5 6".split()


def test_flatter_sep():
    f = html.Flatter([1, 2, 3])
    assert str(f) == "1\n2\n3"
    f.sep = ""
    assert str(f) == "123"
    f = html.Flatter([1, 2, [3, 4, 5]], sep="")
    assert str(f) == "12345"


class UsersTable(html.Table):
    size = 2
    reverse_link = lambda: "/test"

    def __init__(self, paginate=True):
        super().__init__(value=User.objects.order_by("id"), paginate=paginate)

    def soup(self):
        return bs4.BeautifulSoup(str(self), "html.parser")


@pytest.mark.benchmark
def test_flatter_performance(benchmark):
    f = html.Flatter([1, [2], 3, ["a", "b", "c"]])
    benchmark(f.__str__)


def test_table_formatter(db):
    soup = UsersTable(paginate=False).soup()
    print(soup)
    assert soup
    assert len(soup.thead.find_all("th")) == 12


def test_table_pagination_simple(db):
    soup = UsersTable(paginate=False).soup()
    print(soup)
    assert soup


def test_table_pagination_more_pages(users, db):
    for i in range(4):
        users.new(f"usr{i}")
    soup = UsersTable(paginate=False).soup()
    assert not soup.find("div")


@pytest.mark.benchmark
def test_table_benchmark(benchmark, users, db):
    for i in range(4):
        users.new(f"usr{i}")
    table = UsersTable(paginate=False)
    benchmark(table.__str__)
