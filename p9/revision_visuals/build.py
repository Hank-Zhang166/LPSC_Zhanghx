"""Build the figures used in the revised written report and presentation."""
import argparse
from make_figures import architecture, transport, diagnosis, network, two_simulations, validation
from data_panels import mo_curve, weights, rankings

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",action="store_true",help="Also draw the completed redesign runs")
    args=parser.parse_args()
    for fn in (architecture,transport,diagnosis,network,two_simulations,validation,mo_curve,weights,rankings):
        fn()
    if args.model:
        from model_panels import generate
        generate()
