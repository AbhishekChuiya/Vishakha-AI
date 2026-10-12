import ast
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / "ai" / "agent" / "workflow.py"

class WorkflowContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = WORKFLOW.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.code)
        cls.fn = next(n for node in cls.tree.body if isinstance(node, ast.ClassDef) and node.name == "AgentWorkflow"
                      for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "process_message")

    def test_application_mode_keyword_supported(self):
        self.assertIn("application_mode", [a.arg for a in self.fn.args.args])
        self.assertEqual(self.fn.args.defaults[-1].value, "sep")

    def test_phase1_validation_still_present(self):
        self.assertIn("meaningful_description(self.state.description)", self.code)
        self.assertIn('"UNRECOGNIZED"', self.code)

    def test_sep_does_not_call_general_chat(self):
        self.assertNotIn("respond_to_general_chat", ast.get_source_segment(self.code, self.fn))

if __name__ == "__main__":
    unittest.main()
