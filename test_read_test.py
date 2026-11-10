import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, Mock, patch

import read_test


class ReadTestTests(unittest.TestCase):
    def test_runs_200_requests_and_reports_requested_source(self):
        for source in ("redis", "postgres"):
            with self.subTest(source=source):
                response = Mock()
                response.json.return_value = {"total_source": source}
                session = MagicMock()
                session.__enter__.return_value = session
                session.get.return_value = response
                output = io.StringIO()

                with (
                    patch.object(read_test.requests, "Session", return_value=session),
                    patch.object(read_test.time, "sleep"),
                    redirect_stdout(output),
                ):
                    read_test.main([source])

                self.assertEqual(session.get.call_count, 200)
                self.assertTrue(
                    all(
                        call.args[0].endswith(f"/stats?source={source}")
                        for call in session.get.call_args_list
                    )
                )
                self.assertIn(f"maanga  : {source}", output.getvalue())
                self.assertIn(f"'{source}': 200", output.getvalue())
                self.assertIn("p95     :", output.getvalue())
                self.assertIn("slowest :", output.getvalue())


if __name__ == "__main__":
    unittest.main()
