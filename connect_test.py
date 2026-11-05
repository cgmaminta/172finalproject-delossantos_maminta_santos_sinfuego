from apps import dbconnect as db

df = db.getDataFromDB(
    "SELECT current_database(), current_user, inet_server_port(), current_schema()",
    [],
    ['database', 'user', 'port', 'schema'],
)
print(df.to_string())

tables = db.getDataFromDB(
    """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY 1, 2
    """,
    [],
    ['schema', 'table'],
)
print(tables.to_string())