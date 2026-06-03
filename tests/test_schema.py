from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from toolburn.schema import REQUIRED_TABLES, initialize_database, table_names


class SchemaTests(unittest.TestCase):
    def test_initialize_database_creates_required_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "toolburn.sqlite"

            initialize_database(db_path)

            self.assertEqual(table_names(db_path), sorted(REQUIRED_TABLES))


if __name__ == "__main__":
    unittest.main()
