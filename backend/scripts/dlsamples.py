#!/usr/bin/python3

import json
import os
import requests
import sys


def path(storage, uid, name):
    return os.path.join(storage, uid, name)


def download_asset(url, filepath):
    if not url:
        return

    ext = url.rsplit('.', 1)[-1]
    resp = requests.get(url, timeout=5)
    if resp.status_code == 200:
        with open(filepath + '.' + ext, 'wb') as f:
            f.write(resp.content)


def download(comic, storage):
    try:
        uid = comic['objectID']
        mkdir(path(uid, ''))
        download_asset(comic.get('cover', ''), path(uid, 'cover'))
        for i,sample in enumerate(comic.get('samples', [])):
            download_asset(sample, path(storage, uid, 'sample_{}'.format(i)))
    except:
        pass


def mkdir(path):
    try:
        os.makedirs(path)
    except:
        pass


if __name__ == '__main__':
    src = sys.argv[1]
    storage = sys.argv[2]

    with open(src) as lines:
        for line in lines:
            comic = json.loads(line)
            download(comic, storage)
