# Landing-screen flow concepts

**Selected and revised direction:** [Library first — complete app review](library-first-review/README.md).
The 3 November revision applies the requested wording, saved-library startup,
Custom controls, removed bottom tabs and multi-year recovery-signal lesson.
It includes navigation for the entire app, not just the introductory flow.
The earlier three options below remain as historical alternatives.

These proposals were created after publishing APK source **0.6.0**, on
**30 October 2026 (Singapore)**. They are design explorations; the released
application still starts on Parameters. All displayed prices/results are
illustrative, and the clickable prototype does not use live data or app storage.

Open **[landing-flow-options.html](landing-flow-options.html)** in a browser.
It is self-contained and works offline. Switch among three concepts and between
**First visit** and **Returning user**, then click through the phone. Use the
full-size map button for a vector board, or print the page to export all three
boards as PDF. GitHub displays the HTML source; download the file and open it
locally to use the prototype.

| Direction | What the first visit shows | Return visit | Palette | Flow map |
| --- | --- | --- | --- | --- |
| **01 Calm home — recommended** | One primary Start action, one-line SMA explanation, optional sample and guide | Saved company groups on Home, direct View | Sage and cream | [PNG](calm-home.png) · [SVG](calm-home.svg) |
| **02 Guided example** | An optional three-step worked example, with an equally clear skip route | Lesson disappears from the primary path; saved groups take its place | Soft lilac | [PNG](guided-example.png) · [SVG](guided-example.svg) |
| **03 Library first** | A friendly empty library with New analysis and an example card | The same screen becomes the personal SMA library | Midnight and mint | [PNG](library-first.png) · [SVG](library-first.svg) |

## Recommended flow

First visit: **Home → Choose security → Parameters → Results → Save**.
The user can stay on Results after saving, or return Home. Search requires
Enter/Search, and selecting a match loads history, following the existing app
behavior. Parameters shows the company identity and one primary choice:
**Upward crossings per year**. Fictional-pattern settings and technical limits
are folded into Advanced options in this proposal.

Return visit: **Home → saved company group → View → exact saved Results**.
No repeated search or parameter setup is necessary. The first company group can
start open, making its View buttons directly available. Home presents recent
saved lines; Saved leads to the full library and its existing controls. Back
returns to the screen from which the chart was opened. New analysis remains
available at the top of Home.

## Learning without a dense landing page

1. **Before starting:** explain in one sentence that a moving average smooths
   recent closing prices. Offer a short example without making a tour mandatory.
2. **At the frequency choice:** explain what an upward crossing means and that
   frequency matching does not optimize investment returns. Keep the explanation
   next to the relevant control, behind a small information button if expanded.
3. **On the first result:** introduce one action at a time: inspect a chart
   point, pinch to zoom, and save the line. Dismissed tips should stay dismissed;
   Learn can replay them. Charts should keep their quick period controls.
4. **After the first save:** show where the line lives on Home. Keep the full
   saved-menu controls, notification preferences and technical metrics deeper
   in their respective screens. Request phone permission only when a phone
   alert is enabled, rather than during the first launch.
5. **When something goes wrong:** keep the query and parameters on search/load
   failure, and show retry where the action occurred. Empty search results
   should explain how to try again. These are proposed states for implementation,
   not simulated network failures in this static click-through.

The calm home gives beginners a clear next action and repeat users a short path
to their work. The guided option suits users who want a little more teaching;
the library option suits frequent users who already understand the terms. The
layout and palette can be chosen independently.

## What can be tried in the prototype

- All three first-visit and returning-user states.
- Explicit search: type `app` or `micro`, submit, then select a company.
- Frequency choice, contextual help, illustrative Results and a sample chart point.
- Save/unsave, Home/Saved company groups, direct View with the exact example
  period/target, Back and the optional three-step guide.

This is a flow prototype, so charts and results are illustrative rather than a
second implementation of the app. For reproducible review, changing the persona
resets the prototype's in-memory saved examples. Reload also resets them.

Validation in local Chromium exercised all three end-to-end click paths,
explicit search, help, exact saved restoration and optional guide. All three
SVG boards were checked for text overflow in phone frames, and mobile layouts
at 390px had no horizontal overflow. Desktop/mobile screenshots were inspected.

To regenerate the SVG boards and self-contained HTML after editing the source:

```sh
python -m scripts.render_landing_flows
```

The source template is `scripts/landing_flow_template.html`. PNG previews were
rendered from the SVGs with CairoSVG in a separate design-tools environment;
the app has no new runtime dependencies.
