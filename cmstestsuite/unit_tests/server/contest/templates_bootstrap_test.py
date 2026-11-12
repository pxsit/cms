#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2026 Pasit Sangprachathanarak <ouipingpasit@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Check that CWS templates keep to the Bootstrap 2 markup.

cws_style.css restyles Bootstrap 5 to look like Bootstrap 2 and redefines
its grid (.container, .row, spanN), so the Bootstrap 5 grid and utility
classes would be laid out by the Bootstrap 2 rules.

"""

import os
import re
import unittest

import jinja2
from jinja2 import nodes


TEMPLATES = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "cms", "server", "contest", "templates")

# Bootstrap 5 classes that mean something different from, or nothing in,
# the Bootstrap 2 rules of cws_style.css.
FORBIDDEN = re.compile(
    r"^(col(-(sm|md|lg|xl|xxl))?(-\d+)?|row-cols(-.*)?|container-(fluid|sm|"
    r"md|lg|xl|xxl)|g[xy]?-\d|offset(-.*)?-\d+|(d|flex|justify|align|gap|"
    r"m[trblxy]?|p[trblxy]?)-(.+))$")
CLASS_ATTRIBUTE = re.compile(r'class="([^"]*)"')

_JINJA = jinja2.Environment()

# Stands for a value only known when rendering. It is a digit so that a
# prefix completed at run time, as in class="col-{{ n }}", reads "col-0"
# and is caught.
_DYNAMIC = "0"
# Filters that print their operand, possibly changing its case.
_PASS_THROUGH_FILTERS = {
    "e": None, "escape": None, "string": None, "trim": None,
    "lower": str.lower, "upper": str.upper,
}
# Concatenations of several conditional parts are cut at this many outputs.
_MAX_OUTPUTS = 64


def _outputs(node, escaped=True):
    """Return what the expression node can print, as a list of strings.

    String constants that end up in the page are kept: the branches of an
    "a if x else b", the operands of "or" and "and", the parts of a "~" or
    "+" concatenation, and the operands of "|safe", "|default" and the
    filters that only escape or change case. Anything else (a variable, a
    function call, a comparison) prints something unknown, written as
    _DYNAMIC. CWS autoescapes, so a printed double quote cannot end an
    attribute, unless the string is marked safe.

    """
    if node is None:
        return [""]
    if isinstance(node, nodes.Const):
        if not isinstance(node.value, str):
            return [_DYNAMIC]
        return [node.value.replace('"', " ") if escaped else node.value]
    if isinstance(node, nodes.CondExpr):
        return _outputs(node.expr1, escaped) + _outputs(node.expr2, escaped)
    if isinstance(node, (nodes.Or, nodes.And)):
        return _outputs(node.left, escaped) + _outputs(node.right, escaped)
    if isinstance(node, (nodes.Concat, nodes.Add)):
        parts = node.nodes if isinstance(node, nodes.Concat) \
            else [node.left, node.right]
        results = [""]
        for part in parts:
            results = [a + b for a in results
                       for b in _outputs(part, escaped)][:_MAX_OUTPUTS]
        return results
    if isinstance(node, nodes.Filter):
        if node.name == "safe":
            return _outputs(node.node, escaped=False)
        if node.name in ("default", "d"):
            return _outputs(node.node, escaped) + (
                _outputs(node.args[0], escaped) if node.args else [])
        if node.name in _PASS_THROUGH_FILTERS:
            change = _PASS_THROUGH_FILTERS[node.name] or (lambda s: s)
            return [change(s) for s in _outputs(node.node, escaped)]
    return [_DYNAMIC]


def _without_jinja(text):
    """Replace each Jinja tag with what it can print.

    Jinja tags may contain double quotes (as in class="{{ "a" if x }} b"),
    which would end a class attribute early, so they have to go before
    the attributes are looked for; what they print is kept, joined to the
    text around it, since it can be class names or parts of them. Jinja's
    own lexer finds the tags, so strings holding "}}" or escaped quotes
    are handled like Jinja does.

    """
    out = []
    expression = None
    for _, kind, value in _JINJA.lex(text):
        if kind == "variable_begin":
            expression = []
        elif kind == "variable_end":
            node = _JINJA.parse("{{%s}}" % "".join(expression)).body[0]
            out.append(" ".join(_outputs(node.nodes[0])))
            expression = None
        elif expression is not None:
            expression.append(value)
        elif kind == "data":
            out.append(value)
        elif kind in ("block_begin", "comment_begin"):
            out.append(" ")
    return "".join(out)


def find_forbidden_classes(text):
    return [token
            for attribute in CLASS_ATTRIBUTE.findall(_without_jinja(text))
            for token in attribute.split()
            if FORBIDDEN.match(token)]


class TestTemplatesUseBootstrap2Markup(unittest.TestCase):

    def test_no_bootstrap_5_grid_or_utilities(self):
        offenders = []
        for directory, _, names in os.walk(TEMPLATES):
            for name in names:
                if not name.endswith(".html"):
                    continue
                path = os.path.join(directory, name)
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                offenders.extend(
                    "%s: %s" % (os.path.basename(path), token)
                    for token in find_forbidden_classes(text))
        self.assertEqual(offenders, [], "Bootstrap 5 classes found in CWS "
                         "templates, see the note in cws_style.css")

    def test_classes_around_jinja_expressions_are_checked(self):
        self.assertEqual(find_forbidden_classes(
            '<div class="{{ "span6" if x else "span12" }} well d-flex">'),
            ["d-flex"])
        self.assertEqual(find_forbidden_classes(
            '<div class="{{ "col-6" if x else "span12" }} well">'),
            ["col-6"])
        self.assertEqual(find_forbidden_classes(
            '<li{% if x %} class="active"{% endif %}><a class="mt-2">'),
            ["mt-2"])

    def test_only_printed_literals_count_as_classes(self):
        # Compared to, not printed.
        self.assertEqual(find_forbidden_classes(
            '<li class="{{ "active" if page == "p-1" }}">'), [])
        self.assertEqual(find_forbidden_classes(
            '<li class="{{ get_class(x, "mt-1") }}">'), [])

    def test_literals_printed_through_operators_and_filters(self):
        for template, expected in [
                ('<div class="{{ extra or "mt-2" }}">', ["mt-2"]),
                ('<div class="{{ x and "d-none" }}">', ["d-none"]),
                ('<div class="{{ cls|default("d-flex") }}">', ["d-flex"]),
                ('<div class="{{ "mt-2"|e }}">', ["mt-2"]),
                ('<div class="{{ "MT-2"|lower }}">', ["mt-2"]),
                ('<div class="{{ "a " + "mt-2" }}">', ["mt-2"]),
                ('<div class="{{ x|join("mt-2") }}">', []),
        ]:
            with self.subTest(template=template):
                self.assertEqual(find_forbidden_classes(template), expected)

    def test_classes_completed_at_run_time(self):
        for template, expected in [
                ('<div class="col-{{ n }}">', ["col-0"]),
                ('<div class="{{ "mt-" ~ n }}">', ["mt-0"]),
                ('<div class="{{ "span" ~ n }} well">', []),
                ('<div class="span{{ n }} offset{{ m }}">', []),
                ('<div class="{{ "col-md-" ~ ("6" if x else "4") }}">',
                 ["col-md-6", "col-md-4"]),
        ]:
            with self.subTest(template=template):
                self.assertEqual(find_forbidden_classes(template), expected)

    def test_tricky_literals_do_not_hide_classes(self):
        self.assertEqual(find_forbidden_classes(
            '<div class="{{ x|default("}}") }} mt-3">'), ["mt-3"])
        self.assertEqual(find_forbidden_classes(
            '<div class="{{ "a\\"b" }} mt-2">'), ["mt-2"])
        self.assertEqual(find_forbidden_classes(
            '<span>{{ \'<i class="mt-2">\'|safe }}</span>'), ["mt-2"])
        self.assertEqual(find_forbidden_classes(
            '<div class="{# "d-none" #} span4">'), [])


if __name__ == "__main__":
    unittest.main()
