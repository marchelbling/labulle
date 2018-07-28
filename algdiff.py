#!/usr/bin/env python3

import argparse
import copy
import datetime
import json
import sys

from algoliasearch import algoliasearch


ISO8601 = '%Y-%m-%dT%H:%M:%S'


def parse_options():
    parser = argparse.ArgumentParser(description='Update Algolia index from JSONLine data')
    parser.add_argument('--app', type=str, required=True, help='Algolia Application ID')
    parser.add_argument('--index', type=str, required=True, help='Algolia Index')
    parser.add_argument('--key', type=str, required=True, help='Algolia API Key')
    parser.add_argument('--data', type=str, required=True, help='Path to new data')
    return parser.parse_args()


def log(msg):
    sys.stderr.write(msg)


def parse_records(filepath):
    records = []
    with open(filepath, encoding='utf8') as data:
        for record in data:
            try:
                r = json.loads(record.replace('\n', ' ').replace('\t', ' ').replace('\r', '').strip(), encoding='utf8')
                if not r.get('objectID') :
                    log(u"invalid record: ''{}'\n".format(record))
                    continue
                records.append(r)
            except:
                log(u"cannot load record: '{}'\n".format(record))
    return records


def get_index(app, key, index):
    client = algoliasearch.Client(app, key)
    return client.init_index(index)


def make_diff(old_records, new_records):
    diff = []
    old = {r['objectID']: r for r in old_records}
    new = {r['objectID']: r for r in new_records}

    for oid, new_record in new.items():
        if oid not in old:
            diff.append(new_record)
        else:
            old_record = old[oid]
            if any(v != old_record.get(k) for k, v in new_record.items()):
                r = copy.deepcopy(old_record)
                r.update(new_record)
                diff.append(r)
    return diff


if __name__ == '__main__':
    options = parse_options()
    index = get_index(options.app, options.key, options.index)

    new_records = parse_records(options.data)
    old_records = index.get_objects([r['objectID'] for r in new_records]).get('results', [])

    diff = make_diff(old_records, new_records)
    res = index.save_objects(diff)

    sys.stdout.write(json.dumps({
        'request': diff,
        'response': res,
        'created_at': datetime.datetime.utcnow().strftime(ISO8601)
    }))
