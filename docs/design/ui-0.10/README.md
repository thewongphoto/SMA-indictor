# One-screen setup and named SMAs

These screenshots use controlled HTTP responses and fictional prices. Company
names are real; displayed prices/returns are not market observations. Desktop
previews show Android notification timing/scope; they do not demonstrate native
sleeping-phone delivery.

```mermaid
flowchart TD
  Launch[Launch] --> Library[Your library: company groups collapsed]
  Library -->|New analysis| Choose[Choose a security: submitted search]
  Choose -->|Select company / load history| Preferences[Same screen: selected company + animated target and Optimize]
  Preferences --> Results[Chart: line name / sessions and selected target]
  Results -->|Change parameters| Preferences
  Results -->|Magnifier plus| Choose
  Results -->|Heart| Saved[Saved SMA: pencil to name]
  Saved --> Results
  Library -->|Expand company / View| Results
  Results -->|Saved SMAs| Menu[Company groups with named SMA rows and controls]
  Menu -->|View / Hide / Unsave / Notifications| Results
  Menu --> Archive[Recently unsaved: names retained]
  Archive -->|Restore| Library
  Results --> Backtest[Backtesting: contributions, values and comparisons]
  Backtest --> Details[All upward crossings for named line]
  Details -->|Back| Results
  Library --> Guide[Guided example]
  Guide --> Choose
  Gear[Top-right gear on every page] --> Settings[Settings: signal types / OS test / request log / data controls]
  Settings --> Daily[Android daily checks: enabled saved SMAs only]
```

![Choose a security, with no refresh button](choose-security.png)

After selection the heading changes and the lower controls reveal on the same
screen. A still screenshot shows the completed 280ms animation.

![Selected security and revealed target/Optimize](set-preference.png)

![Edit a saved SMA name](rename-line.png)

![Named chart and selected target in the same card](named-chart.png)

![Named SMA in the populated library](named-library.png)

![Backtest without the removed explanatory paragraph](backtesting.png)

![Names retained in the archive](archive.png)

![Singapore-time notification settings](notification-settings.png)
