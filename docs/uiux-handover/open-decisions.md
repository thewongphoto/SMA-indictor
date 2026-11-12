# Original open decisions and missing materials

These questions came with the handover. The implementation resolves them in
[IMPLEMENTATION.md](IMPLEMENTATION.md); this record is retained for context.

## Decisions for the app owner

1. **Alert model on screen 03.** The app has one phone switch per saved line plus three global types (Buy signal; Impending buy signal (End of trading); Impending buy signal (Start of trading)). The prototype shows per-line "Crosses above" / "Crosses below" switches, which match neither. Choose: (a) keep the app's model and show it per line, or (b) allow all three types per line (needs a storage change). Either way, use the app's exact type names.
2. **Expanded cards on launch.** The app closes all groups on launch; the prototype opens the first card. Recommendation: closed, with below-line securities sorted first.
3. **Names versus tickers on Home and chart headers.** Search shows company names first; Home cards in the prototype show tickers first. Recommendation: company name first everywhere, ticker underneath.
4. **Company logo source.** Logos are third-party trademarks; yfinance does not reliably provide them. Choose a licensed source or bundle a small set; use letter circles as fallback.
5. **Download count.** Emails undercount because users can skip. An anonymous install ping would count everyone but goes beyond "email and nothing else". Decide whether to add one; if so, update the first-open wording.
6. **Light theme.** "Follow system setting" was chosen, but only the dark theme is designed.
7. **Legal wording.** The disclaimer is a draft and has not been reviewed by a lawyer.
8. **Proposals 12–18** need review.

## Missing materials

- Manrope font files (download separately; SIL OFL 1.1).
- Real company logos.
- Designs for: Charts tab landing, guided example, restore history (unsaved lines), request log, notification permission denied, landscape and tablet layouts, light theme.
- "Before" screenshots of the current app, for comparison.
