"""Check ordering in DOT output from `terraform graph` for this service.

From an initialised offline service copy with the backend removed, run:
    terraform graph > graph.dot
    python tests/check_dependency_graph.py graph.dot
This checks Terraform dependencies, not Azure operation completion.
"""

from pathlib import Path
import re
import sys
import unittest


class FoundryDependencyTests(unittest.TestCase):
    graph = {}

    def assert_ordered(self, dependent, dependency):
        def reaches(start, target):
            pending, visited = [start], set()
            while pending:
                node = pending.pop()
                if node == target:
                    return True
                if node not in visited:
                    visited.add(node)
                    pending.extend(self.graph.get(node, ()))
            return False

        self.assertTrue(reaches(dependent, dependency),
                        f"No dependency path from {dependent} to {dependency}; operations can overlap")
        self.assertFalse(reaches(dependency, dependent), "The dependency graph contains a cycle")

    def test_project_waits_for_model_and_is_destroyed_first(self):
        self.assert_ordered("azurerm_cognitive_account_project.default", "azurerm_cognitive_deployment.openai")

    def test_project_keeps_private_endpoint_until_deleted(self):
        self.assert_ordered("azurerm_cognitive_account_project.default", "azurerm_private_endpoint.ai_foundry")

    def test_model_keeps_account_until_deleted_and_purged(self):
        self.assert_ordered("azurerm_cognitive_deployment.openai", "azurerm_cognitive_account.ai_foundry")
        self.assert_ordered("azurerm_cognitive_account.ai_foundry", "azapi_resource_action.purge_ai_foundry")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python check_dependency_graph.py graph.dot")
    dot = Path(sys.argv.pop()).read_text()
    for dependent, dependency in re.findall(r'"([^"\n]+)"\s*->\s*"([^"\n]+)"', dot):
        FoundryDependencyTests.graph.setdefault(dependent, set()).add(dependency)
    unittest.main(verbosity=2)
