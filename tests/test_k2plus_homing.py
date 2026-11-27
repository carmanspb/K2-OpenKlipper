"""Render the generated homing macro across partial and complete homing states."""
import importlib.util
import itertools
import unittest
from pathlib import Path
from types import SimpleNamespace

import jinja2

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'k2plus_cfg', ROOT / 'tools/k2plus/make_k2plus_cfg.py')
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def home_commands(homed, axes, state='standby', accel=12345,
                  config='mainline_stage2_k2plus.cfg'):
    text = (ROOT / 'config' / config).read_text()
    body = text.split('[homing_override]\n', 1)[1].split('\n[', 1)[0]
    body = body.split('gcode:\n', 1)[1]
    env = jinja2.Environment(block_start_string='{%', block_end_string='%}',
                             variable_start_string='{', variable_end_string='}')
    def fail(message):
        raise AssertionError(message)
    printer = {
        'toolhead': SimpleNamespace(homed_axes=homed,
                                    position=SimpleNamespace(z=2), max_accel=accel),
        'k2_motor_bus': SimpleNamespace(motors_ready=True),
        'k2_z_align': SimpleNamespace(endstop_triggered=False),
        'print_stats': SimpleNamespace(state=state),
        'filament_switch_sensor filament_sensor': SimpleNamespace(filament_detected=False),
    }
    rendered = env.from_string(body).render(
        params={axis: '0' for axis in axes}, printer=printer, action_raise_error=fail)
    return [line.strip() for line in rendered.splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


class K2PlusHoming(unittest.TestCase):
    def test_generated_file_is_current(self):
        self.assertEqual(generator.apply((ROOT / 'config/mainline_stage2.cfg').read_text()),
                         (ROOT / 'config/mainline_stage2_k2plus.cfg').read_text())

    def test_home_z_homes_only_missing_xy_first(self):
        for homed in ('', 'x', 'y', 'xy', 'z', 'xz', 'yz', 'xyz'):
            with self.subTest(homed=homed):
                commands = home_commands(homed, 'Z')
                for axis in 'xy':
                    self.assertEqual('G28 ' + axis.upper() in commands, axis not in homed)
                    if axis not in homed:
                        self.assertLess(commands.index('G28 ' + axis.upper()),
                                        commands.index('G1 X175 Y175 F12000'))
                self.assertEqual('KZ_ALIGN_BOTTOM CONFIRM=1' in commands, 'z' not in homed)
                self.assertEqual(commands[-1], 'M204 S12345')

    def test_explicit_partial_homes_do_not_trigger_z(self):
        for axes in ('X', 'Y', 'XY'):
            commands = home_commands('', axes)
            self.assertNotIn('KZ_ALIGN_BOTTOM CONFIRM=1', commands)
            self.assertFalse(any('PRTOUCH_HOME_Z' in c for c in commands))
            for axis in 'XY':
                self.assertEqual('G28 ' + axis in commands, axis in axes)

    def test_mesh_homing_preserves_clearance_and_known_axes(self):
        for config in ('mainline_stage2.cfg', 'mainline_stage2_k2plus.cfg'):
            for homed in ('', 'x', 'y', 'xy', 'z', 'xz', 'yz'):
                with self.subTest(config=config, homed=homed):
                    missing = ''.join(a.upper() for a in 'xyz' if a not in homed)
                    commands = home_commands(homed, missing, config=config)
                    for axis in 'XY':
                        self.assertEqual('G28 ' + axis in commands,
                                         axis.lower() not in homed)
                    if 'z' not in homed:
                        clearance = ('KZ_ALIGN_BOTTOM CONFIRM=1'
                                     if 'k2plus' in config else
                                     'FORCE_MOVE STEPPER=stepper_z DISTANCE=5 VELOCITY=10')
                        self.assertIn(clearance, commands)
                        for axis in 'XY':
                            if axis.lower() not in homed:
                                self.assertLess(commands.index(clearance),
                                                commands.index('G28 ' + axis))
                    else:
                        self.assertNotIn('G28 Z', commands)
                        self.assertFalse(any(c.startswith('PRTOUCH_HOME_Z')
                                             for c in commands))

    def test_k2_rejects_z_if_missing_xy_not_requested(self):
        for homed, axes in (('', 'Z'), ('x', 'Z'), ('y', 'Z'),
                            ('', 'XZ'), ('', 'YZ')):
            with self.subTest(homed=homed, axes=axes), self.assertRaisesRegex(
                    AssertionError, 'include missing XY'):
                home_commands(homed, axes, config='mainline_stage2.cfg')

    def test_known_z_never_tours_bottom_in_any_print_state(self):
        for state, axes in itertools.product(('standby', 'printing', 'paused', 'complete'), ('', 'Z')):
            self.assertNotIn('KZ_ALIGN_BOTTOM CONFIRM=1', home_commands('xyz', axes, state))

    def test_stock_xy_travel_then_slow_contact(self):
        commands = home_commands('xyz', 'Z')
        i = commands.index('G1 X175 Y175 F12000')
        self.assertIn('M204 S2000', commands[:i])
        self.assertEqual(commands[i + 1], 'M204 S500')
        self.assertIn('G1 Z5 F1800', commands)
        self.assertIn('PRTOUCH_HOME_Z PROBE_SPEED=1', commands)
        self.assertLess(commands.index('G1 Z5 F1800'),
                        commands.index('PRTOUCH_HOME_Z PROBE_SPEED=1'))


if __name__ == '__main__':
    unittest.main()
