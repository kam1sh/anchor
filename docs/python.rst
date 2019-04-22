Python package index
========================

Protocol overview
-----------------

Python package index protocol describen in the next PEPs:

* Module upload mechanism: PEP 243 https://www.python.org/dev/peps/pep-0243/
* Simple API: PEP 503 https://www.python.org/dev/peps/pep-0503/
* Version identification: PEP 440 https://www.python.org/dev/peps/pep-0440/


So, basically, to make package index you have to
implement a few HTTP endpoints:

GET /
^^^^^


GET /packages/
^^^^^^^^^^^^^^


GET /<package>/
^^^^^^^^^^^^^^^

This endpoint should return simple HTML page
with the list of available versions.
For example, response of GET https://pypi.org/simple/requests/::

    <!DOCTYPE html>
    <html>
    <head>
        <title>Links for requests</title>
    </head>
    <body>
        <h1>Links for requests</h1>
        <a href="https://files.pythonhosted.org/.../requests-0.2.0.tar.gz#sha256=...">requests-0.2.0.tar.gz</a><br/>
        <a href="https://files.pythonhosted.org/.../requests-0.2.1.tar.gz#sha256=...">requests-0.2.1.tar.gz</a><br/>
        <!-- skipped many other versions -->
        <a href="https://files.pythonhosted.org/.../requests-2.21.0-py2.py3-none-any.whl#sha256=..." data-requires-python="&gt;=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*">requests-2.21.0-py2.py3-none-any.whl</a><br/>
        <a href="https://files.pythonhosted.org/.../requests-2.21.0.tar.gz#sha256=..." data-requires-python="&gt;=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*">requests-2.21.0.tar.gz</a><br/>
        </body>
    </html>



.. seealso:: Another useful for understanding web pages:

    - https://packaging.python.org/guides/hosting-your-own-index/
    - Simple server API implementation: https://github.com/pypiserver/pypiserver
    - https://pypi.org/help/
    - DevPI is also interesting example: https://github.com/devpi/devpi
