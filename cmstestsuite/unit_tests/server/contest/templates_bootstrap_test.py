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
JINJA = re.compile(r"{[{%#].*?[}%#]}")


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
                for attribute in CLASS_ATTRIBUTE.findall(text):
                    for token in JINJA.sub(" ", attribute).split():
                        if FORBIDDEN.match(token):
                            offenders.append(
                                "%s: %s" % (os.path.basename(path), token))
        self.assertEqual(offenders, [], "Bootstrap 5 classes found in CWS "
                         "templates, see the note in cws_style.css")


if __name__ == "__main__":
    unittest.main()
