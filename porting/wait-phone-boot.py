import argparse,json,subprocess,time
parser=argparse.ArgumentParser();parser.add_argument("--adb",required=True);parser.add_argument("--serial",required=True);parser.add_argument("--seconds",type=int,default=300);args=parser.parse_args();adb=[args.adb,"-s",args.serial];start=time.monotonic();previous=None
while time.monotonic()-start<args.seconds:
 state=subprocess.run(adb+["get-state"],capture_output=True,text=True,timeout=10)
 status=state.stdout.strip() if state.returncode==0 else state.stderr.strip()
 if status!=previous:print(json.dumps(dict(elapsed=int(time.monotonic()-start),adb=status)),flush=True);previous=status
 if state.returncode==0 and status=="device":
  completed=subprocess.run(adb+["shell","getprop sys.boot_completed"],capture_output=True,text=True,timeout=10)
  if completed.stdout.strip()=="1":
   version=subprocess.check_output(adb+["shell","uname -a"],text=True,timeout=10).strip();print(json.dumps(dict(boot_completed=True,elapsed=int(time.monotonic()-start),uname=version)),flush=True);raise SystemExit(0)
 time.sleep(3)
print("BOOT_WAIT_TIMEOUT",flush=True);raise SystemExit(2)
