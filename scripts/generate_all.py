import os, sys, json, re, shalib, sqlite3


def write_file(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f'[SENTINEL BUILD] Generated: {path}')
