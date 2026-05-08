import argparse
import os
import subprocess
from pathlib import Path


README = '''\
Automatic dataset download is intentionally conservative here.
Some low-light datasets require manual agreement / login / cloud-drive fetch.
This script prepares directories and can download direct URLs when provided.
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=str, default='/home/stonies/projects/llie-stm32/datasets')
    parser.add_argument('--name', type=str, required=True, help='lol | lol_v2 | custom')
    parser.add_argument('--url', type=str, default='', help='Direct downloadable URL if available')
    args = parser.parse_args()

    root = Path(args.root)
    ds = root / args.name
    ds.mkdir(parents=True, exist_ok=True)

    for sub in [
        ds / 'train' / 'low',
        ds / 'train' / 'high',
        ds / 'val' / 'low',
        ds / 'val' / 'high',
    ]:
        sub.mkdir(parents=True, exist_ok=True)

    print(README)
    print(f'prepared dataset skeleton at: {ds}')

    if args.url:
        archive = ds / 'downloaded_archive'
        subprocess.run(['wget', '-O', str(archive), args.url], check=True)
        print(f'downloaded archive to {archive}')
    else:
        print('no URL passed; use this skeleton and place files manually')


if __name__ == '__main__':
    main()
