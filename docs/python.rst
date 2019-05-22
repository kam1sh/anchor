Python repository
========================

TL;DR
-----

::

    # Upload:
    $ poetry config repositories.ci http://localhost/py/upload/
    $ poetry publish --repository ci
    # Search:
    $ pip3 search -i http://localhost/py/ foo

Protocol overview
-----------------

Python packaging has a few API:


Simple API
^^^^^^^^^^

`PEP 503`_ describes *simple* API fith a few operations:

* List of packages - GET /simple/
* List of package files GET /simple/<package>/

.. _`PEP 503`: https://www.python.org/dev/peps/pep-0503/

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


Upload API
^^^^^^^^^^
Upload API is just an POST operation with file and metadata (`specification`_).
A few moments:

- Allowed only next files: .egg, .tar.gz, .whl and .zip (`PEP 527`_);
- Package name should not conflict with Python stdlib;
- It's good to normalize names and versions with,
  for example, module pkg_resources and `packaging`_;

Also, in case of anchor, URI for upload is /py/upload.

.. seealso::

    - `Warehouse upload`_ documentation
    - Warehouse `source code`_

.. _`Warehouse upload`: https://warehouse.pypa.io/api-reference/legacy/#upload-api
.. _`source code`: https://github.com/pypa/warehouse/blob/master/warehouse/forklift/legacy.py#L702
.. _`PEP 527`: https://www.python.org/dev/peps/pep-0527/
.. _`packaging`: https://github.com/pypa/packaging
.. _`specification`: https://packaging.python.org/specifications/core-metadata/

Search
^^^^^^^

There is also search method, that works via `XML RPC`_.
Warehouse has `a bunch`_ of XML RPC, but for pip
implementation of ``search(spec[, operator])`` is enough.
Description of arguments:

- *spec*: dictionary with fields for search.
- *operator*: operator for combination of specifications. Default is "and".

For example, ``search({'name': ['foo'], 'summary': ['foo']}, 'or')``
could be translated as "all packages that name or summary contains 'foo'".

Also, function should return list of dictionaries with fields
"name", "version" and "summary".
Warehouse implementation returns at most 100 packages.

.. _`a bunch`: https://warehouse.pypa.io/api-reference/xml-rpc/
.. _`XML RPC`: https://docs.python.org/3/library/xmlrpc.html

.. seealso::

    - `Warehouse`_ - complete solution that runs pypi.org;
    - `PyPI help`_ contains useful information about python packaging;
    - `PyPI API`_ documentation page;
    - `PEP 440`_, Version identification;
    - `PEP 241`_, Metadata for packages;
    - `PEP 426`_, Metadata for packages 2.0 (withdrawned)
    - https://packaging.python.org;
    - `DevPI`_ is also interesting example;

.. _`Warehouse`: https://github.com/pypa/warehouse
.. _`PEP 440`: https://www.python.org/dev/peps/pep-0440/
.. _`PEP 241`: https://www.python.org/dev/peps/pep-0241/
.. _`PEP 426`: https://www.python.org/dev/peps/pep-0426/
.. _`PyPI API`: https://warehouse.pypa.io/api-reference/
.. _`PyPI help`: https://pypi.org/help/
.. _`DevPI`: https://github.com/devpi/devpi
