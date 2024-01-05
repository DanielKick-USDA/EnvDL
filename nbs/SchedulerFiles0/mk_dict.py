#!/usr/bin/env python

import os, json, re

data = {
#                 'info':[],
# 'nvidia_base_pids_add':[''],
# 'nvidia_base_pids_del':[''],
#     'ipynb_names_read':[],
#      'ipynb_names_add':['notebookName.ipynb'],
#     'ipynb_names_next':['notebookName.ipynb'],
#      'ipynb_names_del':['notebookName.ipynb'],
#      'background_mode':['True'],
#                 'exit':[], 
}


def write_ctrl_json(data: dict):
    ctrl_files = [e for e in os.listdir('./') if (re.match('ctrl.json', e) or re.match('ctrl\d+.json', e))]
    # find the next number to write to. In case 'ctrl.json' and 'ctrl0.json' exist, I'll write to 1
    max_num = [e.replace('ctrl', '').replace('.json', '') for e in  ctrl_files]
    max_num = [int(e) for e in max_num if e != '']
    if max_num == []: max_num = 0
    else: max_num = max(max_num)

    with open(f'./ctrl{max_num+1}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    write_ctrl_json(data = data)
