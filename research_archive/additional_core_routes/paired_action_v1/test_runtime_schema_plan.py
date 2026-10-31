import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build_runtime_schema_plan import main
from unittest import mock


class SchemaPlanTest(unittest.TestCase):
    def test_all_runtime_records_classified(self):
        code = Path(__file__).parent
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'plan.json'
            argv = ['x', '--objects', str(code / 'RUNTIME_OBJECTS_RETRY2.json'),
                    '--report', str(code / 'RUNTIME_REPORT_RETRY2.json'),
                    '--output', str(output)]
            with mock.patch('sys.argv', argv):
                main()
            result = json.loads(output.read_text())
            self.assertEqual(result['records'], 963)
            self.assertFalse(result['unhandled'])
            self.assertEqual(result['class_counts']['static_xml_sha_and_identity'], 202)
            self.assertEqual(result['class_counts']['native_physics_adapter_required'], 2)
            self.assertGreaterEqual(result['class_counts']['renderer_rebuild_and_raster_verifier_required'], 6)
            self.assertFalse(result['dynamic_restore_passed'])


if __name__ == '__main__':
    unittest.main()
