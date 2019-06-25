"""
Tests for HTML formatters.
"""
import bs4

from anchor.common import html
from anchor.users.models import User


def test_flatter_simple():
    f = html.Flatter([1, 2, 3])
    assert list(f) == [1, 2, 3]


def test_flatter_nested():
    f = html.Flatter(["a", [1, 2, 3], "b", "cd", [4, [5], 6]])
    assert list(f) == ["a", 1, 2, 3, "b", "cd", 4, 5, 6]


def test_table_formatter(users, db):
    objects = User.objects.all()
    table = html.Table(objects)
    soup = bs4.BeautifulSoup(str(table), "html.parser")
    print(soup)
    assert soup
    assert len(soup.thead.find_all("th")) == 12
