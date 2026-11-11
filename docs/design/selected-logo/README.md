# Selected app icon: Crosspoint

Proposal 01 was selected for the Android and iPhone app. The finalized master
keeps the orange SMA crossing the turquoise price line and the white plus on
navy. It is fully opaque and square; the operating systems supply their masks.

<img src="../../../sma_analyzer/assets/app-icon.png" width="256" alt="Approved Crosspoint app icon" />

[Open/download the 1024px master](../../../sma_analyzer/assets/app-icon.png).

Android uses a legacy icon plus separate adaptive foreground/background files,
with the complete bright artwork inside the safe circle. This native-mask
preview uses the packaged foreground:

![Android circular mask preview](android-circle.png)

iPhone exports the required AppIcon sizes and the 1024px marketing icon from
the same master. The downloadable Xcode kit preserves the compiled icon
resources and metadata; its verifier checks their hashes after copying.

These are production asset exports from the selected generated proposal, not
a screenshot of an installed phone. Install a successful **0.13.1** build to
see the new launcher icon. Keep the installed app and its signing identity when
upgrading so saved SMAs/cache remain intact.
