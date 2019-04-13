#!/usr/bin/env python3

import argparse
import copy
import datetime
import json
import math
import os
import sys

from algoliasearch import algoliasearch
from dotenv import load_dotenv


ISO8601 = '%Y-%m-%dT%H:%M:%S'


def parse_options():
    parser = argparse.ArgumentParser(description='Update Algolia index from JSONLine data')
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


def fetch_records(object_ids, index):
    records = []
    batch = 1000
    n = math.ceil(len(object_ids or []) / batch)
    for i in range(n+1):
        first = i * 1000
        records.extend(filter(None, index.get_objects(object_ids[first:first+batch]).get('results', [])))
    return records


def get_index(app, key, index):
    client = algoliasearch.Client(app, key)
    return client.init_index(index)


def make_diff(old_records, new_records):
    diff = []
    now = datetime.datetime.utcnow().strftime(ISO8601)
    old = {r['objectID']: r for r in old_records}
    new = {r['objectID']: r for r in new_records}

    for oid, new_record in new.items():
        if oid not in old:
            new_record['created_at']= now
            diff.append(new_record)
        else:
            old_record = old[oid]
            if any(v != old_record.get(k) for k, v in new_record.items()):
                r = copy.deepcopy(old_record)
                r.update(new_record)
                r['updated_at'] = now
                diff.append(r)
    return diff


if __name__ == '__main__':
    load_dotenv()  # source .env
    options = parse_options()
    index = get_index(os.getenv("ALG_APP_ID"), os.getenv("ALG_API_KEY"), os.getenv("ALG_INDEX"))

    new_records = parse_records(options.data)
    old_records = fetch_records([r['objectID'] for r in new_records], index)

    diff = make_diff(old_records, new_records)
    sys.stdout.write('\n'.join(map(json.dumps, diff)))
