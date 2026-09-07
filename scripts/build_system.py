import os, sys, json, shatil, sqlite3, re

def write_file(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f'[SETUP] Written: {path}')

print('Builder framework initialized')
