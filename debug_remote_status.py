
import paramiko
import sys

HOST = "sol.dil.univ-mrs.fr"
PORT = 22
USERNAME = "chevallier"
PASSWORD = "39che67$$+"

def run_remote_command(cmd):
    print(f"Executing: {cmd}")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD)
        stdin, stdout, stderr = client.exec_command(cmd)
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        if out:
            print("--- Output ---")
            print(out)
        if err:
            print("--- Error ---")
            print(err)
            
    except Exception as e:
        print(f"Connection Failed: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    cmds = [
        "hostname",
        "ls -la /space/home/chevallier/InterroPedago",
        "systemctl status interropedago-student",
        "docker ps"
    ]
    for c in cmds:
        print(f"\n>>> {c}")
        run_remote_command(c)
