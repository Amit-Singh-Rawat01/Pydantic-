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
