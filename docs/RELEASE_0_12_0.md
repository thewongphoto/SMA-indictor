# 0.12.0 — Shorter chart views and selectable guide horizons

- The chart dropdown offers **3M, 6M, 9M** before **1Y**, retaining 3Y/5Y/Max.
  Months mean calendar months ending at the latest available close. Month ends
  clamp to the last valid date, including leap years; weekends/missing sessions
  move the start to the next available close. Short histories clamp to available
  data. Chart presets do not change optimization or backtesting inputs.
- Live chart descriptive copy is now just **CCY adjusted daily close** and
  **Dividends and splits included**. CCY is the security's quotation currency.
  The usable-comparisons/search/warm-up paragraph above backtesting is removed.
  Data request failures remain visible through the existing status and log.
- The live guided example still uses **Vanguard S&P 500 ETF (VOO)** and initially
  selects **4/year**, with 1/6/12 also available. Its investment horizon defaults
  to **Max**, with **1Y, 3Y, 5Y, Max and Custom years** selectable. All downloaded
  history is available to Max. The illustrative chart and investment horizon
  remain independent, as in the main analysis screen.
- The guide and main backtesting share horizon-control styling and animated
  Custom inputs. Guide horizon changes recalculate all three scenarios using
  the existing lesson's data/SMA, without another API request or optimization.
  Changing the guide never replaces the user's selected company or saved SMA.

See [phone-width UI captures](design/ui-0.12.0/README.md). Screenshots use controlled
test data; they are not investment results for real VOO prices.

Validation: both Python 3.11 mobile build environments pass the 279-test suite
(one desktop-only check skipped). Running Kivy checks cover the full app,
library navigation, controlled mobile HTTP, chart presets, guide horizons,
320/440px layouts, Custom-input focus/Back, animation and slow-clock loading.

The Android/iPhone build configurations retain their verified source downloads,
package/bundle identity, signing route and on-device data. Release tags are
**apk-v0.12.0** and **ios-v0.12.0**. GitHub's native workflows determine when the
APK and unsigned Xcode kit are ready; the iPhone kit still needs local Personal
Team signing as explained in the [installation guide](PRIVATE_IPHONE_INSTALLATION.md).
