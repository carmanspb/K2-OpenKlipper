"""Exercise the installer migration against a temporary printer filesystem."""
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StockBootRestore(unittest.TestCase):
    def run_migration(self, model, with_backup):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live = root / 'usr/res/boot-play'
            (live / 'part0').mkdir(parents=True)
            (live / 'part1').mkdir()
            (live / 'part0/hark.jpg').write_bytes(b'custom')
            (live / 'desc.txt').write_text('K2 OpenKlipper')
            (live / 'boot.mp3').write_bytes(b'stock audio')
            if with_backup:
                source = root / 'original/boot-play'
                (source / 'part0').mkdir(parents=True)
                (source / 'part1').mkdir()
                (source / 'part0/creality.jpg').write_bytes(b'stock')
                (source / 'desc.txt').write_text('stock descriptor')
                archive = root / 'mnt/UDISK/mainline-backups/boot-play-stock.tar'
                archive.parent.mkdir(parents=True)
                with tarfile.open(archive, 'w') as tar:
                    tar.add(source, arcname='boot-play')
            text = (ROOT / 'install.sh').read_text()
            migration = text.split('# K2 Plus: earlier upstream installers', 1)[1]
            migration = migration.split('# The native touchscreen', 1)[0]
            migration = migration[migration.index('if ['):]
            migration = migration.replace('/mnt/UDISK/', str(root / 'mnt/UDISK') + '/')
            migration = migration.replace('/usr/res', str(root / 'usr/res'))
            subprocess.run(['sh', '-eu', '-c', 'MODEL=' + model + '\n' + migration],
                           check=True, capture_output=True)
            return ((live / 'desc.txt').read_text(),
                    (live / 'part0/hark.jpg').exists(),
                    (live / 'boot.mp3').read_bytes())

    def test_plus_restores_stock_and_removes_custom_frames(self):
        self.assertEqual(self.run_migration('F008', True),
                         ('stock descriptor', False, b'stock audio'))

    def test_other_models_and_missing_backups_are_untouched(self):
        for model, backup in (('F021', True), ('F008', False)):
            self.assertEqual(self.run_migration(model, backup),
                             ('K2 OpenKlipper', True, b'stock audio'))


if __name__ == '__main__':
    unittest.main()
