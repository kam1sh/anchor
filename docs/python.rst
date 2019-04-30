Python package index
========================

Protocol overview
-----------------

Python packaging has a few API:


Simple API
^^^^^^^^^^

PEP 503_ describes *simple* API fith a few operations:

* List of packages - GET /simple/
* List of package files GET /simple/<package>/
* File upload - POST, which URI could be various
  (in case of ciconia it's /upload/).

.. _503: https://www.python.org/dev/peps/pep-0503/

All operations should return (also simple) HTML page
with list of the links like that (copied from warehouse docs)::

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    X-PyPI-Last-Serial: 871501

    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Index</title>
    </head>
    <body>
        <!-- More projects... -->
        <a href="/simple/warehouse/">warehouse</a>
        <!-- ...More projects -->
    </body>
    </html>

.. seealso::
    - Simple API implementation: https://github.com/pypiserver/pypiserver

XML RPC
^^^^^^^

Uh-oh. This API is deprecated, but still used by commands
such as ``pip search``. Will describe later.


.. seealso::

    - `Warehouse`_ - complete solution that runs pypi.org;
    - `PyPI help`_ contains useful information about python packaging;
    - `PyPI API`_ documentation page;
    - `PEP 440`_, Version identification;
    - packaging.python.org;
    - `DevPI`_ is also interesting example;

.. _`Warehouse`: https://github.com/pypa/warehouse
.. _`PEP 440`: https://www.python.org/dev/peps/pep-0440/
.. _`PyPI API`: https://warehouse.pypa.io/api-reference/
.. _`PyPI help`: https://pypi.org/help/
.. _`DevPI`: https://github.com/devpi/devpi