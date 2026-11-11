# Selected app icon: Crosspoint

Proposal 01 was selected for the Android and iPhone app. The finalized master
now shows the turquoise **price crossing upwards from below the orange SMA**,
with a steeper rising price segment and a white plus at the intersection.
It is fully opaque and square; the operating systems supply their masks.

<img src="../../../sma_analyzer/assets/app-icon.png" width="256" alt="Approved Crosspoint app icon" />

[Open/download the 1024px master](../../../sma_analyzer/assets/app-icon.png).

Android uses a legacy icon plus separate adaptive foreground/background files,
with the complete bright artwork inside the safe circle. This native-mask
preview uses the packaged foreground:

![Android circular mask preview](android-circle.png)

The retained native iPhone exporter uses the same master, but native releases
are paused. The future web app must export its manifest/Apple touch icons from
this master as described in the Vercel guide.

These are production asset exports from the selected generated proposal, not
a screenshot of an installed phone. Install a successful current Android build to
see the new launcher icon. Keep the installed app and its signing identity when
upgrading so saved SMAs/cache remain intact.

The Android presplash and iOS launch storyboard use this same master instead
of the default Kivy brand. The calculation overlay draws these exact paths
from left to right; [see the animated UI preview](../ui-0.13.2/README.md).
