# Navigation and interaction flows

GitHub renders these diagrams. Screen numbers refer to [screens.md](screens.md).

## App structure

```mermaid
flowchart TD
  Launch([Launch]) --> S05[05 Startup loading]
  S05 -->|first launch| S06[06 First open: email]
  S05 -->|later launches| Home
  S06 -->|Continue, valid email| Sent[[Send email change to developer]] --> Home
  S06 -->|Skip for now| Home
  subgraph Tabs[Bottom tab bar]
    Home[01 Home]
    Charts[Charts tab: not designed]
    Alerts[03 Alerts]
    Settings[04 Settings]
  end
  Home -->|+ Find SMA| S10[10 Search]
  Home -->|tap security card| Expand[Card expands: saved lines]
  Expand -->|tap a line| S02[02 SMA detail]
  S10 -->|Search or Enter| S11[11 Results]
  S10 -->|tap recent| S02
  S11 -->|Open or Analyse| S02
  S02 -->|scroll| S02b[02b Backtest]
  S02 -->|Find best SMA| S07[07 Optimising] -->|done| S02
  S07 -->|Cancel| S02
  S02 -->|Save| Home
  S02 --> S08[08 Several lines]
  S08 -->|Edit| S09[09 Rename and recolour] -->|Done| S08
  Settings -->|Save or Change email| Sent2[[Send email change to developer]]
```

## Rules

- **Back**: every pushed screen (02, 08, 09, 10, 11) has a visible ‹ Back. Android hardware/gesture Back does the same. The iPhone Home Screen app has no browser Back button, so the on-screen Back is required there.
- **Tabs** keep their own stack; tapping the active tab returns to its root.
- **Sorting on Home**: securities with any line below its SMA first, then the rest; keep saved order within each group.
- **Expanded cards**: the app currently closes all groups on launch. The prototype opens the first card. See open decisions.
- **Search**: one request per Search press. Editing the text does not search. Recent items never trigger a request.
- **Optimising**: cancelling stops the job and ignores any late result. The chart stays as it was.
- **Rename/recolour**: changes apply live; Done closes the sheet. Blank name falls back to "SMA (N days)".
- **Email**: submit and change both send a message to the developer. Skip sends nothing. The email can be added later in Settings.

## Saving and alerts sequence

```mermaid
sequenceDiagram
  participant U as User
  participant A as App
  participant S as Server (planned)
  U->>A: Save line on 02
  A->>A: Store line (existing LineStore.save)
  A-->>U: Line appears on Home and 08
  U->>A: Switch alert types on 03
  Note over A: Android: WorkManager job checks at scheduled SGT times
  Note over S: iPhone web: server scheduler checks and sends Web Push
```
