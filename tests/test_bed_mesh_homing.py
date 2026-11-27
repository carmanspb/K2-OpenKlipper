"""Mesh calibration homes missing axes before probing, through G28 overrides."""
import importlib
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / 'klippy'))
bed_mesh = importlib.import_module('extras.bed_mesh')


class MeshHoming(unittest.TestCase):
    def calibrator(self, homed):
        self.calls = []
        self.homed = set(homed)

        def run(command):
            self.calls.append(command)
            axes = command.split()[1:]
            if 'Z' in axes:
                self.assertTrue(set('xy') <= self.homed)
            requested = set(''.join(axes).lower()) if axes else set('xyz')
            self.assertFalse(requested & self.homed)
            self.homed.update(requested)

        def probe(gcmd):
            self.assertEqual(self.homed, set('xyz'))
            self.calls.append('probe')

        toolhead = SimpleNamespace(get_status=lambda now: {'homed_axes': homed})
        cal = bed_mesh.BedMeshCalibrate.__new__(bed_mesh.BedMeshCalibrate)
        cal.printer = SimpleNamespace(
            lookup_object=lambda name: toolhead,
            get_reactor=lambda: SimpleNamespace(monotonic=lambda: 123.))
        cal.gcode = SimpleNamespace(run_script_from_command=Mock(side_effect=run))
        cal.bedmesh = SimpleNamespace(set_mesh=Mock())
        cal.update_config = Mock()
        cal.probe_mgr = SimpleNamespace(start_probe=Mock(side_effect=probe))
        return cal

    def test_every_homing_state(self):
        cases = {'': ['G28'], 'x': ['G28 Y', 'G28 Z'],
                 'y': ['G28 X', 'G28 Z'], 'z': ['G28 X Y'],
                 'xy': ['G28 Z'], 'xz': ['G28 Y'], 'yz': ['G28 X'],
                 'xyz': []}
        for homed, commands in cases.items():
            with self.subTest(homed=homed):
                cal = self.calibrator(homed)
                gcmd = SimpleNamespace(get=lambda key, default: default)
                cal.cmd_BED_MESH_CALIBRATE(gcmd)
                self.assertEqual(self.calls, commands + ['probe'])
                cal.update_config.assert_called_once_with(gcmd)
                cal.probe_mgr.start_probe.assert_called_once_with(gcmd)

    def test_homing_failure_prevents_probing(self):
        cal = self.calibrator('xy')
        cal.gcode.run_script_from_command.side_effect = RuntimeError('home failed')
        with self.assertRaisesRegex(RuntimeError, 'home failed'):
            cal.cmd_BED_MESH_CALIBRATE(SimpleNamespace(get=lambda k, d: d))
        cal.probe_mgr.start_probe.assert_not_called()

    def test_invalid_config_does_not_home(self):
        cal = self.calibrator('')
        cal.update_config.side_effect = bed_mesh.BedMeshError('invalid mesh')
        with self.assertRaisesRegex(ValueError, 'invalid mesh'):
            cal.cmd_BED_MESH_CALIBRATE(SimpleNamespace(
                get=lambda k, d: d, error=ValueError))
        cal.gcode.run_script_from_command.assert_not_called()
        cal.probe_mgr.start_probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
