import ast
import unittest
from pathlib import Path


CONSUMER_PATH = Path(__file__).with_name("consumer.py")


class FakePartition:
    def __init__(self, partition):
        self.partition = partition


class ConsumerLagTests(unittest.TestCase):
    def test_metrics_server_and_labelled_results_are_declared(self):
        source = CONSUMER_PATH.read_text(encoding="utf-8")
        compose_source = (
            CONSUMER_PATH.parent / "docker-compose.yml"
        ).read_text(encoding="utf-8")
        prometheus_source = (
            CONSUMER_PATH.parent / "prometheus.yml"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)

        start_server_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "start_http_server"
        ]

        self.assertEqual(len(start_server_calls), 1)
        self.assertIn('ports:\n      - "8001:8001"', compose_source)
        for result in ("saved", "duplicate", "rejected", "db_error"):
            self.assertIn(f'result="{result}"', source)
        self.assertIn('job_name: "consumer"', prometheus_source)

    def test_event_histogram_times_processing_but_not_batch_commit(self):
        source = CONSUMER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        histogram = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "EVENT_SECONDS"
                for target in node.targets
            )
        )

        self.assertIsInstance(histogram, ast.Call)
        self.assertEqual(histogram.func.id, "Histogram")
        self.assertEqual(
            ast.literal_eval(histogram.keywords[0].value),
            (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        )

        message_loop = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and node.target.id == "message"
        )
        timing_block = next(
            node
            for node in message_loop.body
            if isinstance(node, ast.With)
            and isinstance(node.items[0].context_expr, ast.Call)
            and isinstance(node.items[0].context_expr.func, ast.Attribute)
            and isinstance(node.items[0].context_expr.func.value, ast.Name)
            and node.items[0].context_expr.func.value.id == "EVENT_SECONDS"
        )
        self.assertTrue(
            any(
                isinstance(node, ast.If)
                and "slow.on" in ast.unparse(node.test)
                for node in timing_block.body
            )
        )
        self.assertFalse(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "event_done"
                for node in ast.walk(timing_block)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.If)
                and any(
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "event_done"
                    for child in ast.walk(node)
                )
                for node in message_loop.body
                if node is not timing_block
            )
        )

    def test_update_lag_sums_partition_end_minus_position(self):
        source = CONSUMER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        update_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "update_lag"
        )
        namespace = {}

        class FakeLag:
            def __init__(self):
                self.value = None

            def set(self, value):
                self.value = value

        namespace["LAG"] = FakeLag()
        exec(compile(ast.Module(body=[update_node], type_ignores=[]), str(CONSUMER_PATH), "exec"), namespace)

        partitions = [FakePartition(0), FakePartition(1)]
        end_offsets = {partitions[0]: 100, partitions[1]: 205}
        positions = {partitions[0]: 90, partitions[1]: 200}

        class FakeConsumer:
            def assignment(self):
                return set(partitions)

            def end_offsets(self, _partitions):
                return end_offsets

            def position(self, partition):
                return positions[partition]

        namespace["update_lag"](FakeConsumer())
        after = namespace["LAG"].value

        self.assertEqual(after, 15)

    def test_empty_assignment_leaves_lag_unmodified(self):
        source = CONSUMER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        update_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "update_lag"
        )
        namespace = {}

        class FakeLag:
            def __init__(self):
                self.value = 7

            def set(self, value):
                self.value = value

        namespace["LAG"] = FakeLag()
        exec(compile(ast.Module(body=[update_node], type_ignores=[]), str(CONSUMER_PATH), "exec"), namespace)

        class FakeConsumer:
            def assignment(self):
                return set()

        namespace["update_lag"](FakeConsumer())
        after = namespace["LAG"].value

        self.assertEqual(after, 7)


if __name__ == "__main__":
    unittest.main()
