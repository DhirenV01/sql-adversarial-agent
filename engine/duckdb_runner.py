import re
import duckdb

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_identifier(name: str) -> str:
    """
    Validate and quote a SQL identifier to prevent injection.
    Rejects anything that isn't a simple alphanumeric/underscore name,
    then double-quotes it for safe interpolation.
    """
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


class DuckDBRunner:
    """
    Executes SQL queries against an in-memory DuckDB instance.
    Each runner instance is isolated — create a new one per test run.

    Supports context manager protocol for automatic cleanup:
        with DuckDBRunner() as runner:
            runner.setup_schema(ddl)
            ...
    """

    def __init__(self):
        self.conn = duckdb.connect(database=":memory:")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def setup_schema(self, ddl: str) -> None:
        """
        Execute one or more CREATE TABLE statements.
        ddl can contain multiple statements separated by semicolons.
        """
        statements = [s.strip() for s in ddl.split(";") if s.strip()]
        for statement in statements:
            self.conn.execute(statement)

    def insert_rows(self, table_name: str, rows: list[dict]) -> None:
        """
        Insert a list of row dicts into a table.
        All rows must have the same keys. Table and column names are
        validated and quoted to prevent SQL injection.
        """
        if not rows:
            return

        safe_table = _quote_identifier(table_name)
        columns = list(rows[0].keys())
        safe_columns = [_quote_identifier(c) for c in columns]
        col_str = ", ".join(safe_columns)
        placeholders = ", ".join(["?" for _ in columns])
        sql = f"INSERT INTO {safe_table} ({col_str}) VALUES ({placeholders})"

        for row in rows:
            values = [row[col] for col in columns]
            self.conn.execute(sql, values)

    def run_query(self, sql: str) -> list[dict]:
        """
        Run a SQL query and return results as a list of dicts.
        Returns an empty list if the query produces no rows.
        """
        cursor = self.conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def load_and_run(
        self,
        ddl: str,
        rows_by_table: dict[str, list[dict]],
        query: str,
    ) -> list[dict]:
        """
        Convenience method: set up schema, insert all rows, run query.
        rows_by_table: {"table_name": [{"col": val, ...}, ...]}
        """
        self.setup_schema(ddl)
        for table_name, rows in rows_by_table.items():
            self.insert_rows(table_name, rows)
        return self.run_query(query)

    def reset(self) -> None:
        """Drop everything and start fresh."""
        self.conn.close()
        self.conn = duckdb.connect(database=":memory:")

    def close(self) -> None:
        self.conn.close()
