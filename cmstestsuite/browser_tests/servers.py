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

"""Start the CMS web servers that the browser tests drive."""

import contextlib
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator


def executable(name: str) -> str:
    """Return the path of a CMS command of this environment.

    Only this environment's commands run the code under test, so there is
    no fallback to other installations on the PATH.

    """
    path = os.path.join(sys.prefix, "bin", name)
    if not os.access(path, os.X_OK):
        raise RuntimeError(
            "cannot find %s in %s: install CMS in the environment running "
            "the tests" % (name, os.path.dirname(path)))
    return path


def _port_in_use(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex((parts.hostname, parts.port)) == 0


@contextlib.contextmanager
def run_server(name: str, args: list[str], url: str) -> Iterator[str]:
    """Run the CMS service name with args until url answers, yield url,
    and stop the service on exit.

    Any HTTP answer below 500 (a page, a redirect to the login, a 403)
    means that the server is up. Something else already listening on the
    port is an error, as the tests would otherwise drive it instead.

    """
    if _port_in_use(url):
        raise RuntimeError(
            "something is already listening at %s; stop it (maybe a %s left "
            "over from an earlier run) before running the tests" % (url, name))
    verbose = os.environ.get("CMS_BROWSER_TEST_VERBOSE")
    proc = subprocess.Popen(
        [executable(name)] + args,
        stdout=None if verbose else subprocess.DEVNULL,
        stderr=None if verbose else subprocess.STDOUT)
    hint = "(set CMS_BROWSER_TEST_VERBOSE=1 to see its output)"
    try:
        deadline = time.monotonic() + 60
        while True:
            if proc.poll() is not None:
                raise RuntimeError("%s exited early with code %s %s"
                                   % (name, proc.returncode, hint))
            try:
                urllib.request.urlopen(url, timeout=2).close()
                break
            except urllib.error.HTTPError as error:
                if error.code < 500:
                    break
                failure = "answered %d" % error.code
            except (urllib.error.URLError, OSError) as error:
                failure = str(error)
            if time.monotonic() > deadline:
                raise RuntimeError("%s did not come up (last attempt: %s) %s"
                                   % (name, failure, hint))
            time.sleep(0.3)
        if proc.poll() is not None:
            raise RuntimeError("%s exited with code %s while starting %s"
                               % (name, proc.returncode, hint))
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
