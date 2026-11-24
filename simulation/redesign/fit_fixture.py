"""Exercise both version branches on a naturally requested update in joint sensitivity."""
import csv
import json

from engine import run
from run_study import OUT,dump


def fixture():
    with (OUT/"joint_sensitivity.csv").open(encoding="utf-8") as f:
        row=next(r for r in csv.DictReader(f) if r["policy"]=="tree_fit" and r["metric"]=="fit_count" and float(r["difference"])>0)
    get=lambda k:float(row[k])
    cfg=dict(freeze_h=get("freeze_h"),speed={"review":get("review_scale")},budget_diagnostic=round(get("budget")),
             screen_quality=get("screen_quality"),truth_global=get("actual_global"),truth_repair=get("actual_repair"),
             batch_pass_if_target=get("batch_separation"),batch_pass_if_nontarget=1-get("batch_separation"))
    for seed in range(933400,933496):
        r,_=run(seed,"baseline","tree_fit",overrides=cfg)
        if r["fit_count"]:break
    else:raise AssertionError("unreplayable sensitivity fit")
    for accept,dest in [(1.,"fit_events.csv"),(0.,"rollback_events.csv")]:
        _,events=run(seed,"baseline","tree_fit",record=True,overrides=dict(cfg,truth_accept=accept))
        assert any(e["event"]==("version_published" if accept else "rollback") for e in events)
        dump(dest,events)
    (OUT/"fit_fixture.json").write_text(json.dumps(dict(profile=int(row["profile"]),seed=seed,conditional_branches=[1,0],
          source="First sampled joint design with a voluntary fit; forcing accept/reject illustrates implementation only.",
          overrides=cfg),indent=2),encoding="utf-8")
if __name__=="__main__":fixture()
