"""Elapsed-time checks for a spinner, independent of a CI renderer's FPS."""


def observe_spinner(samples, started, ended, period=.9, maximum_gap=.3):
    intervals=[b[0]-a[0] for a,b in zip(samples,samples[1:])]
    degrees=sum((b[1]-a[1])%360 for a,b in zip(samples,samples[1:]))
    observed=samples[-1][0]-samples[0][0] if len(samples)>1 else 0
    expected=observed*360/period
    report={"sample_seconds":ended-started,"frames":len(samples),
            "rotation_degrees":degrees,"largest_frame_interval":max(intervals,default=0),
            "first_update_delay":max(0,samples[0][0]-started) if samples else ended-started,
            "last_update_delay":max(0,ended-samples[-1][0]) if samples else ended-started,
            "observed_seconds":observed,"rotation_to_clock_ratio":degrees/expected if expected else 0}
    problems=[]
    if degrees<=1080:
        problems.append("Spinner did not continue beyond three revolutions.")
    if any(gap<0 for gap in intervals) or max(report["largest_frame_interval"],
            report["first_update_delay"],report["last_update_delay"])>=maximum_gap:
        problems.append("Spinner updates stalled during the observation.")
    if not .8<=report["rotation_to_clock_ratio"]<=1.2:
        problems.append("Spinner rotation did not keep pace with elapsed time.")
    return report,problems
