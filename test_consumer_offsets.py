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

    def test_postgres_insert_is_idempotent_by_kafka_coordinates(self):
        self.assertIn("pg_insert(models.Error)", self.source)
        self.assertIn("kafka_partition=message.partition", self.source)
        self.assertIn("kafka_offset=message.offset", self.source)
        self.assertIn("stmt.on_conflict_do_nothing(", self.source)
        self.assertIn('"kafka_partition"', self.source)
        self.assertIn('"kafka_offset"', self.source)

    def test_duplicate_delivery_skips_incident_and_realtime_counters(self):
        guarded_blocks = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Attribute)
            and isinstance(node.test.value, ast.Name)
            and node.test.value.id == "insert_result"
            and node.test.attr == "rowcount"
        ]

        self.assertEqual(len(guarded_blocks), 2)
        guarded_calls = {
            node.func.id
            for block in guarded_blocks
            for node in ast.walk(block)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }
        self.assertIn("check_and_create_incident", guarded_calls)
        self.assertIn("update_realtime_counters", guarded_calls)


if __name__ == "__main__":
    unittest.main()