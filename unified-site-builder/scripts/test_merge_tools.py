import unittest,tempfile,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stage',HERE/'stage_app.py');stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
class MergeToolsTests(unittest.TestCase):
 def test_mirror_updates_files_preserves_source_and_drops_stale_staging_entries(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source=root/'app';target=root/'stage';source.mkdir();target.mkdir();(source/'a.txt').write_text('new');(target/'a.txt').write_text('old');(target/'stale.txt').write_text('stale');(source/'data').mkdir();(source/'data'/'private.txt').write_text('runtime data')
   result=stage.mirror(source,target,exclude=('data',));self.assertEqual((target/'a.txt').read_text(),'new');self.assertFalse((target/'stale.txt').exists());self.assertFalse((target/'data').exists());self.assertEqual((source/'data'/'private.txt').read_text(),'runtime data');self.assertEqual(result['removed'],1)
 def test_mirror_refuses_overlapping_paths_before_writing(self):
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'app';source.mkdir();(source/'keep.txt').write_text('preserve')
   with self.assertRaises(ValueError):stage.mirror(source,source/'staging')
   with self.assertRaises(ValueError):stage.mirror(source,source)
   self.assertEqual((source/'keep.txt').read_text(),'preserve')
if __name__=='__main__':unittest.main()
