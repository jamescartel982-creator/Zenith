"""Inspect or validate Zenith's source-backed model and dataset registry."""
import argparse
import json
from agent.registry import Catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', default=None)
    parser.add_argument('--kind', choices=['model', 'dataset'], default=None)
    parser.add_argument('--source', choices=['huggingface', 'github'], default=None)
    parser.add_argument('--query', default='')
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--page-size', type=int, default=20)
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    catalog = Catalog(args.directory)
    result = {'valid': True, 'counts': catalog.counts, 'snapshots': catalog.snapshots} if args.validate else catalog.search(args.kind, args.source, args.query, args.page, args.page_size)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
