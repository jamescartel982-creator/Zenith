"""Reconstruct byte-exact inactive research weights into a new directory."""
import argparse
import json
from pathlib import Path
from agent.research import materialize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(materialize(args.bundle,args.output),indent=2))


if __name__=='__main__':main()
