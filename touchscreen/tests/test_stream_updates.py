"""Exercise partial updates in the actual renderer, including retained state."""
import copy
import unittest
import test_native_ui as native


class StreamUpdates(unittest.TestCase):
    setUp = native.NativeUI.setUp
    render = native.NativeUI.render

    def patch(self, values, remove=(), session=None):
        return {'_screen_patch': True, 'session': session or self.data['session'],
                'set': values, 'remove': list(remove)}

    def pixels(self):
        return (self.path / 'screen.ppm').read_bytes()

    def test_partial_heater_update_matches_complete_state(self):
        changed = copy.deepcopy(self.data)
        changed['heaters'][0].update(current=187, target=210)
        self.render('heat', [{'snapshot': changed}])
        expected = self.pixels()
        self.render('heat', [{'snapshot': self.patch({'heaters': changed['heaters']})}])
        self.assertEqual(self.pixels(), expected)

    def test_sequential_updates_and_explicit_removal_match_full_snapshot(self):
        state = copy.deepcopy(self.data)
        state['platform']['starting_file'] = 'example.gcode'
        self.data = state
        changed = copy.deepcopy(state)
        del changed['platform']['starting_file']
        changed['heaters'][1]['target'] = 70
        self.render('heat', [{'snapshot': changed}])
        expected = self.pixels()
        self.render('heat', [{'snapshot': self.patch({'platform': changed['platform']})},
                             {'snapshot': self.patch({'heaters': changed['heaters']})}])
        self.assertEqual(self.pixels(), expected)

    def test_wrong_session_patch_does_not_change_rendered_values(self):
        self.render('heat')
        expected = self.pixels()
        self.render('heat', [{'snapshot': self.patch({'heaters': []}, session='stale')}])
        self.assertEqual(self.pixels(), expected)

    def test_full_reconnect_after_patch_and_reordered_config(self):
        changed = copy.deepcopy(self.data)
        changed['settings'] = dict(reversed(list(changed['settings'].items())))
        self.render('heat', [{'snapshot': changed}])
        expected = self.pixels()
        self.render('heat', [{'snapshot': self.patch({'heaters': []})}, {'snapshot': changed}])
        self.assertEqual(self.pixels(), expected)
