#!/usr/bin/python3
import json
import sys


if __name__ == '__main__':
    src, dst = sys.argv[1:3]

    lines = []
    with open(src, encoding='utf8') as source:
        for line in source:
            js = json.loads(line)
            if js.get('objectID'):
                lines.append(js)

    with open(dst, 'w') as output:
        json.dump(lines, output)
