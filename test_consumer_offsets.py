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

    def test_offsets_are_committed_in_batches_after_processing_paths(self):
        kafka_commit_calls = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "commit"
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "self"
            and node.func.value.attr == "consumer"
        ]

        self.assertEqual(len(kafka_commit_calls), 1)
        self.assertIn("committer = BatchCommitter(consumer)", self.source)
        self.assertEqual(self.source.count("committer.event_done()"), 2)
        self.assertIn("self.pending >= self.every", self.source)
        self.assertIn("self.interval", self.source)
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

    def test_crash_hook_runs_after_database_commit_before_offset_commit(self):
        self.assertIn(
            "CRASH_AFTER = int(sys.argv[1]) if len(sys.argv) > 1 else 0",
            self.source,
        )
        insert_position = self.source.index("insert_result = db.execute(stmt)")
        crash_position = self.source.index("os._exit(1)")
        database_commit_position = self.source.index(
            "db.commit()", insert_position
        )
        offset_commit_position = self.source.index(
            "committer.event_done()", crash_position
        )

        self.assertLess(insert_position, crash_position)
        self.assertLess(database_commit_position, crash_position)
        self.assertLess(crash_position, offset_commit_position)
        self.assertLess(
            self.source.index("update_realtime_counters(validated_event.service_name)"),
            crash_position,
        )
        self.assertIn("saved_this_run == CRASH_AFTER", self.source)
        self.assertIn('"[SKIP] pehle se delivered;', self.source)


if __name__ == "__main__":
    unittest.main()