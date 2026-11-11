"""Elapsed-time checks for loading feedback, independent of a CI renderer's FPS."""


def observe_logo(samples, started, ended, period=1.4, maximum_gap=.3):
    intervals=[b[0]-a[0] for a,b in zip(samples,samples[1:])]
    observed=samples[-1][0]-samples[0][0] if len(samples)>1 else 0
    elapsed=samples[-1][1]-samples[0][1] if len(samples)>1 else 0
    report={"sample_seconds":ended-started, "frames":len(samples),
            "completed_cycles":samples[-1][1]/period if samples else 0,
            "largest_frame_interval":max(intervals,default=0),
            "first_update_delay":max(0,samples[0][0]-started) if samples else ended-started,
            "last_update_delay":max(0,ended-samples[-1][0]) if samples else ended-started,
            "elapsed_to_clock_ratio":elapsed/observed if observed else 0}
    problems=[]
    if report["completed_cycles"]<2:
        problems.append("Logo did not continue through two complete drawing cycles.")
    if any(gap<0 for gap in intervals) or max(report["largest_frame_interval"],
            report["first_update_delay"],report["last_update_delay"])>=maximum_gap:
        problems.append("Logo updates stalled during the observation.")
    if not .8<=report["elapsed_to_clock_ratio"]<=1.2:
        problems.append("Logo drawing did not keep pace with elapsed time.")
    return report,problems
