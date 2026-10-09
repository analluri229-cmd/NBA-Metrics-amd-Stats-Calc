"""Minimal Basketball-Reference table reader built on the standard library.

Every Basketball-Reference cell carries a stable ``data-stat`` name, player
cells carry the player slug in ``data-append-csv`` and many numeric cells keep a
full-precision value in ``csk``. This reads those attributes directly instead
of relying on the displayed column headers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class Cell:
    stat: str
    text: str
    csk: str | None = None
    slug: str | None = None


@dataclass
class Row:
    css_class: str
    cells: list[Cell] = field(default_factory=list)

    @property
    def slug(self) -> str | None:
        return next((cell.slug for cell in self.cells if cell.slug), None)

    def text(self, stat: str) -> str | None:
        return next((cell.text for cell in self.cells if cell.stat == stat), None)


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: dict[str, list[Row]] = {}
        self._table: str | None = None
        self._in_body = False
        self._row: Row | None = None
        self._cell: Cell | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table":
            self._table = attributes.get("id") or f"table_{len(self.tables)}"
            self.tables.setdefault(self._table, [])
        elif tag == "tbody" and self._table:
            self._in_body = True
        elif tag == "tr" and self._in_body:
            self._row = Row(attributes.get("class") or "")
        elif tag in ("td", "th") and self._row is not None:
            self._cell = Cell(attributes.get("data-stat") or "", "", attributes.get("csk"),
                              attributes.get("data-append-csv"))
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._cell.text = "".join(self._text).strip()
            self._row.cells.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._table:
                self.tables[self._table].append(self._row)
            self._row = None
        elif tag == "tbody":
            self._in_body = False
        elif tag == "table":
            self._table = None


def read_tables(html: str) -> dict[str, list[Row]]:
    """Return {table id: body rows}. Tables hidden in HTML comments are included."""
    parser = _TableParser()
    parser.feed(re.sub(r"<!--|-->", "", html))
    parser.close()
    return parser.tables
