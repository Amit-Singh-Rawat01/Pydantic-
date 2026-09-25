import ast
import unittest
from pathlib import Path


CONSUMER_PATH = Path(__file__).with_name("consumer.py")


class ConsumerOffsetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONSUMER_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_auto_commit_is_disabled(self):
        consumer_calls = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "KafkaConsumer"
        ]

        self.assertEqual(len(consumer_calls), 1)
        keywords = {
            keyword.arg: keyword.value
            for keyword in consumer_calls[0].keywords
        }
        self.assertIsInstance(keywords["enable_auto_commit"], ast.Constant)
        self.assertFalse(keywords["enable_auto_commit"].value)

    def test_offsets_are_committed_manually_after_processing_paths(self):
        commit_calls = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "commit"
        ]

        self.assertGreaterEqual(len(commit_calls), 2)
        self.assertIn("consumer.commit()", self.source)
        self.assertIn("rejected_saved = save_rejected_event", self.source)


if __name__ == "__main__":
    unittest.main()