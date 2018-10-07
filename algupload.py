#!/usr/bin/env python3

import argparse
import json
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


def get_index(app, key, index):
    client = algoliasearch.Client(app, key)
    return client.init_index(index)


if __name__ == '__main__':
    load_dotenv()  # source .env
    options = parse_options()
    index = get_index(os.getenv("ALG_APP_ID"), os.getenv("ALG_API_KEY"), os.getenv("ALG_INDEX"))

    new_records = parse_records(options.data)
    res = index.save_objects(new_records)
    print(res)
