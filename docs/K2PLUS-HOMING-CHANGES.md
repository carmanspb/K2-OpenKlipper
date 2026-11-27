# K2 Plus boot and homing changes

These changes target F008 (K2 Plus). The regular K2 configuration is unchanged.

The installer restores `/mnt/UDISK/mainline-backups/boot-play-stock.tar` when
available. Earlier upstream installers saved Creality's animation there before
installing the Hark Tech frames. Fresh installs leave Creality's animation in
place. If that backup is missing on an already modified printer, the installer
cannot reconstruct the original frames; recover them from a stock firmware
backup. The native touchscreen itself does not install a replacement animation.

`G28 Z` now homes missing Y/X axes before travelling to the probe point, including
when sent directly from a console. Already homed X/Y axes are preserved.
Re-homing a known Z no longer visits the bottom switches first.

An unknown Z still uses the bottom switches outside a print. This includes the
first Z home after a restart or motor release, even if X/Y have just been homed.
The previous implementation records false early triggers during a full-height
strain-gauge search; simply deleting the bottom reference would reintroduce
that failure. Eliminating this first reference trip requires supervised hardware
validation of the initial probe search. Explicit `KZ_ALIGN_BOTTOM` remains
available; print-start alignment behavior is unchanged.

Stock K2 Plus motion values restored:

| Setting | Previous | New |
| --- | ---: | ---: |
| Maximum XY acceleration | 20,000 mm/s² | 30,000 mm/s² |
| Maximum Z travel speed | 20 mm/s | 30 mm/s |
| Maximum Z acceleration | 500 mm/s² | 1,000 mm/s² |
| XY travel to the Z-home point | 100 mm/s | 200 mm/s |
| Acceleration for that XY travel | 500 mm/s² | 2,000 mm/s² |
| Known-coordinate Z approach to 5 mm | 10 mm/s | 30 mm/s |

X/Y homing remains 100 mm/s, Z coarse homing remains 5 mm/s, and the precision
contact tap remains 1 mm/s. The known-coordinate Z approach uses the restored
30 mm/s travel limit; the final 5 mm clearance move stays at 10 mm/s. The homing macro restores the acceleration active
before homing, including after an X-only or Y-only home. Touchscreen jogging
retains its separate 50 mm/s XY limit; stock homing/travel values do not establish
a safe replacement for that manual-control limit.

Sources: Creality's [F008 printer.cfg](https://github.com/CrealityOfficial/K2_Series_Klipper/blob/main/config/F008_CR0CN240319C13/printer.cfg)
and [sensorless.cfg](https://github.com/CrealityOfficial/K2_Series_Klipper/blob/main/config/F008_CR0CN240319C13/sensorless.cfg).
The local stock configuration comparison also confirms 800 mm/s XY,
30,000 mm/s² XY, and 30 mm/s / 1,000 mm/s² Z limits.

Validation: rendered macro tests cover every combination of homed axes, explicit
X/Y/XY requests, known-Z re-homing in idle/printing/paused/complete states,
acceleration restoration, stock travel speed, and generator reproducibility.
Installer tests restore an actual temporary tar archive and check model scoping,
missing-backup behavior, custom-frame removal, and retained boot audio.
No live printer movement has been performed for this branch.
