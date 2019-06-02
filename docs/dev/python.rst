Python repository
=================

Protocol overview
-----------------

Python packaging has a few API: a *Simple API*, *upload* and a *search API*.


Simple API
^^^^^^^^^^

`PEP 503`_ describes *simple* API fith a few operations:

* List of packages - GET /simple/
* List of package files GET /simple/<package>/

.. _`PEP 503`: https://www.python.org/dev/peps/pep-0503/

All operations should return (also simple) HTML page
with list of the links like that (copied from Warehouse docs)::

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
Upload API is just an POST operation with file archive and metadata.
One moment: Allowed only next files: .egg, .tar.gz, .whl and .zip (`PEP 527`_),
but Anchor supports only .tar.gz (sdist) and .whl (wheel) .

.. seealso::

    - `Warehouse upload`_ documentation
    - And its `source code`_

.. _`Warehouse upload`: https://warehouse.pypa.io/api-reference/legacy/#upload-api
.. _`source code`: https://github.com/pypa/warehouse/blob/master/warehouse/forklift/legacy.py#L702
.. _`PEP 527`: https://www.python.org/dev/peps/pep-0527/


---

.. seealso::

    - `Warehouse`_ - complete solution that runs pypi.org
    - `PyPI help`_ contains useful information about python packaging
    - `PyPI API`_ documentation page
    - `PEP 440`_, Version identification
    - `PEP 241`_, Metadata for packages
    - `PEP 426`_, Metadata for packages 2.0 (withdrawned)
    - https://packaging.python.org
    - `DevPI`_ is also interesting example

.. _`Warehouse`: https://github.com/pypa/warehouse
.. _`PEP 440`: https://www.python.org/dev/peps/pep-0440/
.. _`PEP 241`: https://www.python.org/dev/peps/pep-0241/
.. _`PEP 426`: https://www.python.org/dev/peps/pep-0426/
.. _`PyPI API`: https://warehouse.pypa.io/api-reference/
.. _`PyPI help`: https://pypi.org/help/
.. _`DevPI`: https://github.com/devpi/devpi



Reference
---------

API views
^^^^^^^^^

.. automodule:: anchor.pypi.views
  :members:

Models
^^^^^^

.. automodule:: anchor.pypi.models
    :members:
