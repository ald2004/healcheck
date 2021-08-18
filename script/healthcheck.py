#! /usr/bin/python
#
#
# Copyright (C) 2013-2014 Canonical
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#
# Syntax:
# 	health-check-test-pid.py pid
#
# The process name is resolved and the tool will use a `procname`.threshold file
# to compare against.  If this file does not exist, default.threshold is used.
#
import sys, os, json, psutil
# import from local directory libleveldb.so
import leveldb
import fire
import multiprocessing
import time
import requests
import json

#
# Processes we don't want to run health-check on
#
ignore_procs = ['health-check', 'sh', 'init', 'cat', 'vi', 'emacs ', 'getty', 'csh', 'bash']

#
# Default test run durations in seconds
#
default_duration = 6

#
# Parse thresholds file:
#    lines starting with '#' are comments
#    format is: key value, e.g.
#       health-check.cpu-load.cpu-load-total.total-cpu-percent  0.5
#       health-check.cpu-load.cpu-load-total.user-cpu-percent   0.5
#       health-check.cpu-load.cpu-load-total.system-cpu-percent 0.5
#
LEVELDB_NAME = "leveldb"


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    WARNING_RED = '\x1b[31m'
    WARNING_RED_END = '\x1b[0m'


class dns:
    SITE_ONE = "http://39.98.184.81"  # 8325.gr792d04.f0ezq5ws.e87a2d.grapps.cn
    SITE_B = "http://8325.gr792d04.f0ezq5ws.e87a2d.grapps.cn"


mycolor = bcolors
mydns = dns


def update_ruleid_processid(ruleid: int, processid: int):
    db = leveldb.DB(f"/dev/shm/{LEVELDB_NAME}".encode('utf-8'))
    db.put(f"rule_id_{ruleid:05d}".encode('utf-8'), f"{processid}".encode('utf-8'))
    db.close()


def _init_leveldb():
    default_health_dict = {
        "health-check.cpu-load.cpu-load-total.total-cpu-percent": "10",
        "health-check.network-connections.network-connections-total.receive-total-rate": "100"
    }
    db = leveldb.DB(f"/dev/shm/{LEVELDB_NAME}".encode('utf-8'), create_if_missing=True)
    db.put(b"health-check.keys", ';'.join(list(default_health_dict.keys())).encode('utf-8'))
    for k, v in default_health_dict.items():
        db.put(k.encode('utf-8'), v.encode('utf-8'))

    # for key, value in db:
    #     print(f"the key is :{key.decode('utf-8')} ----->  value is : {value.decode('utf-8')}")


def read_threshold_fromdb(init_leveldb=False):
    if init_leveldb:
        _init_leveldb()
    db = leveldb.DB(f"/dev/shm/{LEVELDB_NAME}".encode('utf-8'), create_if_missing=True)
    monitor_keys = db.get(b'health-check.keys').decode('utf-8').split(';')
    thresholds = {}
    n = 0
    try:
        for k in monitor_keys:
            n = n + 1
            thresholds[k] = db.get(k.encode('utf-8')).decode('utf-8')
    except:
        # print(k.encode('utf-8'))
        # print( db.get(k.encode('utf-8')).decode('utf-8'))
        # raise
        pass
    db.close()
    return thresholds


def check_threshold(data, key, fullkey, threshold):
    try:
        d = data[key[0]]
    except:
        sys.stderr.write("health-check JSON data does not have key " + fullkey + "\n")
        return (True, "Attribute not found and ignored")

    key = key[1:]
    if len(key) > 0:
        return check_threshold(d, key, fullkey, threshold)
    else:
        val = float(d)
        if threshold >= val:
            cmp = str(threshold) + " >= " + str(val)
            return (True, cmp)
        else:
            cmp = str(threshold) + " < " + str(val)
            return (False, cmp)


def check_thresholds(procname, data, thresholds):
    print(f"process: {procname}")
    failed = False
    for key in thresholds.keys():
        if key.startswith("health-check"):
            (ret, str) = check_threshold(data, key.split('.'), key, float(thresholds[key]))
            if ret:
                msg = "PASSED"
            else:
                msg = "FAILED"
                failed = True
            sys.stderr.write(msg + ": " + str + ": " + key + "\n")
    return failed


#
#  run health-check on a given process
#
def health_check(pid, procname, thresholds):
    print(f"now check process : {pid}...")
    duration = default_duration
    if 'duration' in thresholds:
        duration = int(thresholds['duration'])
    filename = "/tmp/health-check-" + str(pid) + ".log"
    cmd = "health-check -c -f -d " + str(duration) + " -w -W -r -p " + str(pid) + " -o " + filename + " > /dev/null"
    try:
        os.system(cmd)
    except:
        sys.stderr.write("Failed to run " + cmd + "\n");
        return
    try:
        f = open(filename, 'r')
        data = json.load(f)
        f.close()
    except:
        sys.syderr.write("Failed to open JSON file " + filename + "\n");
        return
    return check_thresholds(procname, data, thresholds)


def send_api_url(ruleid: int):
    print(f"{mycolor.OKCYAN}send ruleid:{ruleid} offline message ...{mycolor.ENDC}")
    # PARAMS = {
    #     "id": f"{ruleid}"
    # }
    # curl -X PUT -H  "Accept:*/*" -H  "Request-Origion:Knife4j" -H  "Content-Type:application/x-www-form-urlencoded" "http://8325.gr792d04.f0ezq5ws.e87a2d.grapps.cn/api/rule/error/0"
    HEADER = {
        "Request-Origion": "Knife4j",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # r = requests.put(url=f"http://{mydns.SITE_B}/api/rule/error/{ruleid}", headers=HEADER)
    r = requests.put(url=f"{mydns.SITE_B}/api/rule/error/{ruleid}", headers=HEADER)
    try:
        xx = json.loads(r.text)
        # {"success":true,"code":0,"message":"业务处理成功","data":false}
        if xx.get('code'):
            print(
                f"{mycolor.WARNING_RED} send message error: code is {xx.get('code')},message is :{xx.get('message')}{mycolor.WARNING_RED_END}")
        else:
            print(
                f"{mycolor.OKGREEN}send ruleid:{ruleid},{xx.get('message')},return code is:{xx.get('code')},return flag:{xx.get('success')}{mycolor.ENDC}")
    except Exception as e:
        print(f"{mycolor.WARNING_RED} {sys.exc_info()[0]}{mycolor.WARNING_RED_END}")
    time.sleep(1)


def monitor_process(ruleid: int, pid: int):
    if pid < 99:
        return
    try:
        p = psutil.Process(pid)
    except:
        sys.stderr.write("Cannot find process with PID " + str(pid) + "\n")
        return

    try:
        pgid = os.getpgid(pid)
    except:
        sys.stderr.write("Cannot find pgid on process with PID " + str(pid) + "\n")
        return

    if pgid == 0:
        sys.stderr.write("Cannot run health-check on kernel task with PID " + str(pid) + "\n")
        return
    try:
        procname = os.path.basename(p.name())
        if p.name in ignore_procs:
            sys.stderr.write(f"the {procname} , is in ignore_procs")
            return
        else:
            #
            #  Did it fail?
            #
            # print('1111111111111', flush=True)
            thres = read_threshold_fromdb()
            # print('333333333333333333333333', flush=True)
            if (health_check(pid, procname, thres)):
                print(f"health_check return true")

                return
            else:
                print(f"[health_check]: alg rule {ruleid}, is offline!! now send api. ")
                send_api_url(ruleid)
                return
    except:
        sys.stderr.write("An execption occurred, failed to test on PID " + str(pid) + "\n")
        print(f"p.name is {p.name()}")
        raise


def show_leveldb():
    db = leveldb.DB(f"/dev/shm/{LEVELDB_NAME}".encode('utf-8'), create_if_missing=True)
    for key, value in db:
        print(f"the key is :{key.decode('utf-8')} ----->  value is : {value.decode('utf-8')}")
    db.close()


def dothework(init_leveldb=False):
    thres = read_threshold_fromdb(init_leveldb)
    # print(f"thres is : {thres}")
    # for i in range(99):
    update_ruleid_processid(886, 886)
    update_ruleid_processid(1057, 1057)
    # show_leveldb()
    ruleid_processid = {}
    db = leveldb.DB(f"/dev/shm/{LEVELDB_NAME}".encode('utf-8'), create_if_missing=True)
    for key, value in db.range(start_key=b'rule_id_00000', end_key=b'rule_id_99999', start_inclusive=False,
                               end_inclusive=False):
        ruleid_processid[key.decode('utf-8')] = int(value.decode('utf-8'))
        # monitor_process(int(value.decode('utf-8')))
        # print(int(value.decode('utf-8')))
        # monitor_process
    db.close()
    print(ruleid_processid)

    mppool = []
    for k, v in ruleid_processid.items():
        try:
            ruleid = k.split('_')[-1]
            p = multiprocessing.Process(target=monitor_process, args=(int(ruleid), int(v)))
            # monitor_process(int(ruleid), int(v))
            p.start()
            mppool.append(p)
        except:
            print(f"rule id:{k},deal error.")
    for p in mppool:
        try:
            p.join()
        except:
            pass


if __name__ == '__main__':
    fire.Fire()
