Python packages support
=======================

Anchor has support for the Python packages (sdist and wheel)
and API that is compatible with pip, twine and others.



TL;DR
-----

::

    # Upload:
    $ poetry config repositories.ci http://localhost/py/upload/
    $ poetry publish --repository ci
    # Search:
    $ pip3 search -i http://localhost/py/ foo

.. TODO write more!

