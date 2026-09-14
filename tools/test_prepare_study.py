"""Regression checks for staging without destroying local work; no Unreal required."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from prepare_study import ROOT, prepare


class PreparationTests(unittest.TestCase):
    def setUp(self):
        default = Path('F:/DevCache/SyntySenceLearning/tests') if os.name == 'nt' and Path('F:/').exists() else ROOT / '.local/tests'
        self.scratch = Path(os.environ.get('SYNTY_TEST_SCRATCH', default)).resolve()
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='prepare-', dir=self.scratch)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(self.scratch)
        self.project = self.root / 'Study.uproject'
        self.project.write_text(json.dumps({'FileVersion': 3, 'Plugins': []}), encoding='utf-8')
        self.target = self.root / 'Learning/SyntySenceLearning/polygon-apocalypse/02-city-ground'

    def tearDown(self):
        # TemporaryDirectory owns only this checked scratch child.
        assert self.root.is_relative_to(self.scratch) and self.root != self.scratch
        self.temp.cleanup()

    def test_dry_run_and_idempotency(self):
        original = self.project.read_bytes()
        prepare(self.project, 'city-ground', dry_run=True)
        self.assertFalse(self.target.exists())
        first = prepare(self.project, 'city-ground')
        second = prepare(self.project, 'city-ground')
        self.assertGreater(first['copied_or_updated_files'], 0)
        self.assertEqual(second['copied_or_updated_files'], 0)
        self.assertEqual(self.project.read_bytes(), original)

    def test_local_edit_is_preserved(self):
        prepare(self.project, 'city-ground')
        edited = self.target / 'Scripts/build_city_ground.py'
        edited.write_text('# local user edit\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'locally edited'):
            prepare(self.project, 'city-ground')
        self.assertEqual(edited.read_text(), '# local user edit\n')

    def test_directory_conflict_rejected_before_copy(self):
        self.target.mkdir(parents=True)
        (self.target / 'Scripts').write_text('keep me', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'directory is occupied'):
            prepare(self.project, 'city-ground')
        self.assertFalse((self.target / 'README.md').exists())
        self.assertFalse((self.target / 'study.json').exists())

    def test_marker_symlink_cannot_write_outside(self):
        self.target.mkdir(parents=True)
        outside = self.root / 'outside.json'
        outside.write_text('{}', encoding='utf-8')
        try:
            (self.target / '.prepared-study.json').symlink_to(outside)
        except OSError as exc:
            self.skipTest('Symlink creation unavailable: ' + str(exc))
        with self.assertRaisesRegex(ValueError, 'marker'):
            prepare(self.project, 'city-ground')
        self.assertEqual(outside.read_text(), '{}')
        self.assertFalse((self.target / 'README.md').exists())


if __name__ == '__main__':
    unittest.main()
