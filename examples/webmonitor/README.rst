Web monitor
-----------

Run as:
::

    python main.py

or by using the ``twistd`` daemon architecture:
::

    twistd -ny main.py

Start a log monitor at address:
`<http://localhost:8070/log>`_

And then on another tab the `index <http://localhost:8070/>`_ page. This request should be logged on the log page requested earlier.
