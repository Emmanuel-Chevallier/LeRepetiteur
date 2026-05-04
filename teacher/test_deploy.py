import os
import paramiko
from pathlib import Path

HOST = "sol.dil.univ-mrs.fr"
PORT = 22
USERNAME = "chevallier"
PASSWORD = "39che67$$+"
REMOTE_TARGET_DIR = "/space/home/chevallier/InterroPedago/data"
LOCAL_DATA_DIR = Path(__file__).parent / "data"

def main():
    print("Fetching remote files...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD)
    
    stdin, stdout, stderr = client.exec_command(f"find {REMOTE_TARGET_DIR} -type f -printf '%P\\t%s\\n'")
    remote_map = {}
    for line in stdout:
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            remote_map[parts[0]] = int(parts[1])
    
    print(f"Remote files found: {len(remote_map)}")
    
    target = "students/0023/probabilites/quiz_1"
    print(f"Checking {target} remotely:")
    for k, v in remote_map.items():
        if k.startswith(target):
            print(f"  Remote: {k} (Size: {v})")
            
    print(f"Checking {target} locally:")
    local_dir = LOCAL_DATA_DIR / target
    if local_dir.exists():
        for file in local_dir.iterdir():
            if file.is_file():
                local_size = file.stat().st_size
                rel_path = f"{target}/{file.name}"
                status = "NEW"
                if rel_path in remote_map:
                    if remote_map[rel_path] == local_size:
                        status = "UNCHANGED"
                    else:
                        status = f"MODIFIED (Remote: {remote_map[rel_path]}, Local: {local_size})"
                print(f"  Local: {file.name} (Size: {local_size}) -> Action: {status}")

if __name__ == "__main__":
    main()
