"""Write planning templates. Rows in these files represent no completed work."""
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent


def write(name, header, rows):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows([header, *rows])


def main():
    rng = random.Random(910427)
    powders, pellets = [], []
    for stage, groups, choices in (
        ("screening", ["S1", "S2"], [f"{x/10:.1f}" for x in range(7)]),
        ("unseen_confirmation", ["V1", "V2"], ["A", "B"]),
    ):
        for block in groups:
            order = list(choices)
            rng.shuffle(order)
            for i, value in enumerate(order, 1):
                powder = f"P9-{block}-B{i:02}"
                powders.append([powder, block, stage, value, i,
                                "standard_SOP_pending", "planned", 910427])
                pellets.append([powder.replace("-B", "-M"), powder, stage,
                                "primary_standard", "planned", ""])
    write("powders.csv", ["powder_id","block","stage","nominal_x_or_locked_arm","sequence",
                          "sop","status","registration_seed"], powders)
    write("pellets.csv", ["pellet_id","parent_powder_id","stage","condition","status",
                          "measurement_id"], pellets)

    write("action_registry.csv",
          ["action","level","precondition","resources","published_observation",
           "updates","cannot_establish","alternatives","hold_cancel_resume",
           "time_and_cost_source"], [
        ["standard_powder","phase","approved_SOP;material","staff;furnace;glovebox",
         "batch ancestry and processing QC","sample","phase or EIS pass",
         "reschedule or drop","cancel before irrevocable operation;afterward follow facility",
         "site log pending; simulation/p9/site.json scenario"],
        ["phase_check","phase","identified_powder","XRD;composition;review",
         "phase;residual LiCl;lattice or stoichiometry","structure_support","unique local order;conductivity",
         "composition retest","hold for queue/QC;cancel unopened","same"],
        ["local_assay","structure","compatible phase;competing states","external or permitted NMR/neutron/PDF;review",
         "average occupancy or local-pair statistics","structure_weights","atomic labels;macroscopic pass",
         "hold several hypotheses","reserve;defer;cancel before travel when allowed","transport/service/review separately"],
        ["press_split","sample","preserved paired mass;allowed protocol","press;EIS;review",
         "within-powder measured contrast","sample_mapping","new powder replication;atomic model error",
         "density;geometry;repeat mounting","cancel before consuming sample","paired instrument log pending"],
        ["repeat_eis","measurement","mounting or spectrum concern","EIS;review",
         "technically repeatable fit","measurement","independent batch variance",
         "refix sample;fit review","pause before scan;reassess upon publish","same"],
        ["independent_batch","sample","locked A/B and standard conditions","staff;furnace;XRD;press;EIS;review",
         "independent new batch result","confirmation","single-crystal dynamics",
         "new independent repeat","protect commitments;abort after QC by SOP","same"],
        ["run_md","sampling","compatible structure;valid model","shared GPU",
         "independent trajectories;cross-cage events;transport CI","transport_distribution",
         "macroscopic pass;DFT reference","extend or enlarge cell",
         "reserve asynchronously;retain rework cost","GPU kernel/runtime log"],
        ["independent_dft","atomic","alignment;isolated diagnostics;reference signature","DFT;review",
         "same-frame energy/forces;barrier section","bias_belief","sample concentration;occupancy probability",
         "cheap same-frame force probe","wait or cancel before queue start","DFT queue and convergence log"],
        ["fit_release","atomic","published decision-relevant DFT discrepancy;feasible deadline","DFT;GPU;review",
         "passed or failed acceptance;model_id","potential_version","real sample sign reversal",
         "fixed model;defer one project","train only when budget permits;retain previous version",
         "training;acceptance;deployment and redo logs"],
        ["selective_redo","atomic","new model valid;modifiable dependent task","GPU;review",
         "replacement MD or prediction evidence","transport_distribution","validity of older unrelated tasks",
         "keep result with old model_id","cancel unopened stale work;preserve history","same"],
    ])
    write("event_fields.csv", ["field","meaning","unit_or_type","required_when","status"], [
        ["project_id","stable project parent","ID","all","planned"],
        ["candidate_id","composition and SOP arm","ID","all","planned"],
        ["task_id","work and dependencies","ID","all","planned"],
        ["event_id","append-only event identity","ID","all","planned"],
        ["event_type","submit;queue;start;done;release;defer;cancel;resume;freeze;fail;retry","enum","all","planned"],
        ["event_utc","timezone-qualified timestamp","ISO 8601","all","planned"],
        ["sample_id and parent_powder_id","specimen and independent ancestry","ID","sample task","planned"],
        ["frame_id and trajectory_id","input frame and parent path","ID","compute task","planned"],
        ["model_id and valid_from","prediction mechanism and release time","ID/time","compute task","planned"],
        ["reference_id","code;functional;pseudopotential;convergence;units","ID","reference task","planned"],
        ["resource_id and slot","stable equipment, reviewer or compute","ID","committed stage","planned"],
        ["calendar_revision","shift, planned maintenance and outside load","ID","queue decision","planned"],
        ["committed_spend and actual_spend","reservation and accrued spend","CNY","submission/execution","planned"],
        ["sample_amount","available and consumed aliquot","mg","wet task","planned"],
        ["qc_status and failure_code","quality decision and reason","enum","release/retry","planned"],
        ["observable_uri and uncertainty","result reference, units, uncertainty and source","structured","release","planned"],
        ["proposed_action and rationale","legal alternative, expected loss and disposition","structured","decision","planned"],
    ])


if __name__ == "__main__":
    main()
