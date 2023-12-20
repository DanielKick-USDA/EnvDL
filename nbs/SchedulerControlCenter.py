#!/usr/bin python

import os, re, subprocess, json, time

def write_ctrl_json(data: dict):
    ctrl_files = [e for e in os.listdir('./SchedulerFiles/') if (re.match('ctrl.json', e) or re.match('ctrl\d+.json', e))]
    # find the next number to write to. In case 'ctrl.json' and 'ctrl0.json' exist, I'll write to 1
    max_num = [e.replace('ctrl', '').replace('.json', '') for e in  ctrl_files]
    max_num = [int(e) for e in max_num if e != '']
    if max_num == []: max_num = 0
    else: max_num = max(max_num)

    with open(f'./SchedulerFiles/ctrl{max_num+1}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class Scheduler():
    def __init__(self, background_mode = False, run_main = False):
        self.background_mode = background_mode
        self.exit = False
        self.nvidia_base_pids = []
        self.nvidia_state = {}
        self._init_nvidia()
        self.ipynb_names = []
        if run_main:
            self.main()


    def _init_nvidia(self):
        self._read_nvidia()
        self.nvidia_base_pids = list(self.nvidia_state.keys())

    def _read_nvidia(self):    
        x = subprocess.run("nvidia-smi", shell=True, check=True,  capture_output=True)

        x = str(x).split('\\n')

        table_blocks = [i for i in range(len(x)) if re.match('.+===+.+', x[i])]
        table_breaks = [i for i in range(len(x)) if re.match('.+---+.+', x[i])]
        process_row  = [i for i in range(len(x)) if re.match('.+ Processes: .+', x[i])]
        start_line = [i for i in table_blocks if i > process_row[0] ][0]
        end_line   = [i for i in table_breaks if i > process_row[0] ][0]

        running_processes = [x[i] for i in range(start_line+1, end_line)]
        running_processes = [dict(zip(
            ['GPU', 'GI', 'CI', 'PID', 'Type', 'ProcessName', 'GPUMem'],
            [e for e in line.strip('|').split(' ') if e != ''])) for line in running_processes]

        for e in running_processes:
            self.nvidia_state[e['PID']] = e
    
    def _parse_ctrl_jsons(self):
        ctrl_files = [e for e in os.listdir('./SchedulerFiles/') if (re.match('ctrl.json', e) or re.match('ctrl\d+.json', e))]
        if len(ctrl_files) >= 1:
            for ctrl_file in ctrl_files:            
                with open('./SchedulerFiles/'+ctrl_file, 'r') as f:
                    data = json.load(f)

                keys = tuple(data.keys())

                if 'info' in keys:
                    print("""
This scheduling tool uses json files to modify its state while running. 
It will look for json files beginning with 'ctrl' and containing 0 or more digits in 
./SchedulerFiles/ and then run each. This json should be interpretable as a python dictionary.
Files are interpreted in the order of the keys but conflicting orders are not recommended. 
Example file:
{
    'info'                :[],                            -> Print this message
    'nvidia_base_pids_add':['40082'],                     -> Prevent a specific PID from being autoclosed. (e.g. if you're running a gpu session interactively)
    'nvidia_base_pids_del':['40082'],                     -> Allow a specific PID to be autoclosed.
    'ipynb_names_read'    :[],                            -> Print currently queued notebooks.
    'ipynb_names_add'     :['SchedulerTestScript.ipynb'], -> Add a notebook (to the end) of the queue
    'ipynb_names_next'    :['SchedulerTestScript.ipynb'], -> Add a notebook to the beginning of the queue (does not need to be in the queue)
    'ipynb_names_del'     :['SchedulerTestScript.ipynb'], -> Remove a notebook from the queue
    'background_mode'     :['True'],                      -> Set to idle if there are no notebooks in the queue
    'exit'                :[],                            -> Remove a notebook from the queue
                          
}""")
                for key in keys:
                    if 'nvidia_base_pids_add' == key:
                        self.nvidia_base_pids += data[key]
                    if 'nvidia_base_pids_del' == key:
                        self.nvidia_base_pids = [e for e in self.nvidia_base_pids if e not in data[key]]
                    if 'ipynb_names_read' == key:
                        print(self.ipynb_names)
                    if 'ipynb_names_add' == key:
                        self.ipynb_names += data[key]
                    if 'ipynb_names_next' == key:
                        # technically this could be used to add files and set them to first
                        if data[key] not in self.ipynb_names:
                            self.ipynb_names = data[key]+[e for e in self.ipynb_names  if e != data[key]]
                        else:
                            self.ipynb_names = [e for e in self.ipynb_names  if e == data[key]]+[e for e in self.ipynb_names  if e != data[key]]                        
                    if 'ipynb_names_del' == key:
                        self.ipynb_names = [e for e in self.ipynb_names if e != data[key]]
                    if 'background_mode' == key:
                        dat = data[key][0]
                        if type(dat) == str:
                            if dat.lower() == 'true':
                                dat = True
                            elif dat.lower() == 'false':
                                dat = False
                            else:
                                print(f'{dat} not interpretable as True or False')
                        if type(dat) == bool:
                            self.background_mode = dat
                    if 'exit' == key:
                        self.exit = True

                # remove the file
                os.unlink('./SchedulerFiles/'+ctrl_file)

    def _advance_queue(self):
        if len(self.ipynb_names) == 0:
            pass
        else:
            ipynb_name = self.ipynb_names.pop(0)
            if os.path.exists(ipynb_name) == False:
                pass
            else:
                process = subprocess.Popen(
                    f"conda run -n fastai jupyter execute {ipynb_name}".split(), stdout=subprocess.PIPE
                    )
                output, error = process.communicate()

    def main(self):
        while ((len(self.ipynb_names) > 0) or (self.background_mode)):
            if ((len(self.ipynb_names) == 0) and (self.background_mode)):
                # if idling in background mode wait to check for new commands. 
                time.sleep(10)
                # While idling any new gpu PIDs should be ignored.
                self._init_nvidia()

            if self.exit: break        
            self._parse_ctrl_jsons()

            if self.exit: break
            if (len(self.ipynb_names) > 0):
                print(f'Running {self.ipynb_names[0]}')
                self._advance_queue()

                # allow for external controls
                self._parse_ctrl_jsons()
                if self.exit: break        

                self._read_nvidia()
                # kill all the processes that were not running at the start. 
                for gpu_pid in [e for e in self.nvidia_state.keys() if e not in self.nvidia_base_pids]:
                    subprocess.run(f'kill -9 {gpu_pid}', shell=True)
            print(f'Running {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
        print(    f'Exiting {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')

if __name__=='__main__':
    Scheduler(background_mode = True, run_main=True)
    # shlr = Scheduler()
    # shlr.nvidia_base_pids, shlr.nvidia_state
    # os.listdir('./SchedulerFiles/')
    # write_ctrl_json(data = {
    # 'info':[],
    # 'nvidia_base_pids_add':[''],
    # 'nvidia_base_pids_del':[''],
    # 'ipynb_names_read':[],
    # 'ipynb_names_add':['02.01_g2fc_intercept_model.ipynb'],
    # 'ipynb_names_read':[],
    # 'ipynb_names_next':[''],
    # 'ipynb_names_del':[''],
    # })

    # shlr._parse_ctrl_jsons()
    # shlr.main()

