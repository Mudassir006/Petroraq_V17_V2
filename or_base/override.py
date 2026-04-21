"""Keep file intentionally minimal.

Historically this module overrode `http.db_filter` globally based on
`HTTP_X_ODOO_DBFILTER`. That behavior can affect all DB routing and startup.
It is disabled for production stability.
"""