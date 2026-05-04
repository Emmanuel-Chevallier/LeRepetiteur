
import os
import paramiko
from pathlib import Path
import stat

# --- CONFIGURATION ---
HOST = "sol.dil.univ-mrs.fr"
PORT = 22
USERNAME = "chevallier"
PASSWORD = "39che67$$+"
REMOTE_TARGET_DIR = "/space/home/chevallier/InterroPedago/data"
LOCAL_DATA_DIR = Path(__file__).parent / "data"

def get_remote_tree(sftp, remote_dir, rel_path=""):
    """Recursively build a set of relative file paths from remote."""
    tree = set()
    try:
        for filename in sftp.listdir(remote_dir):
            full_remote_path = f"{remote_dir}/{filename}"
            full_rel_path = f"{rel_path}/{filename}".strip("/")
            
            try:
                rstat = sftp.stat(full_remote_path)
                if stat.S_ISDIR(rstat.st_mode):
                    tree.update(get_remote_tree(sftp, full_remote_path, full_rel_path))
                else:
                    tree.add(full_rel_path)
            except Exception as e:
                print(f"Warning access {full_remote_path}: {e}")
    except Exception as e:
        print(f"Warning listing {remote_dir}: {e}")
        
    return tree

def get_local_tree(local_dir):
    """Recursively build a set of relative file paths from local."""
    tree = set()
    for root, dirs, files in os.walk(local_dir):
        if "temp" in dirs: 
            dirs.remove("temp")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
            
        for file in files:
            if file.startswith("."): continue
            
            abs_path = Path(root) / file
            rel_path = str(abs_path.relative_to(local_dir))
            tree.add(rel_path)
    return tree

def main():
    print(f"🔍 Starting Integrity Check...")
    
    # 1. Local Tree
    print("Reading Local Data Files...")
    local_files = get_local_tree(LOCAL_DATA_DIR)
    print(f"✅ Found {len(local_files)} files locally.")
    
    # 2. Remote Tree
    print("Reading Remote Data Files (SFTP)...")
    try:
        transport = paramiko.Transport((HOST, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        remote_files = get_remote_tree(sftp, REMOTE_TARGET_DIR)
        
        sftp.close()
        transport.close()
        print(f"✅ Found {len(remote_files)} files remotely.")
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 3. Compare
    missing_remote = local_files - remote_files
    extra_remote = remote_files - local_files
    
    print("\n--- RESULTS ---")
    if not missing_remote:
        print("🟢 SUCCESS: All local files are present on the server.")
    else:
        print(f"🔴 ERROR: {len(missing_remote)} files are MISSING on the server:")
        for f in list(missing_remote)[:10]:
            print(f"  - {f}")
        if len(missing_remote) > 10: print("  ... (and others)")
        
    if extra_remote:
        print(f"\n🟠 INFO: {len(extra_remote)} extra files on server (orphans):")
        # Optional: Print a few
        for f in list(extra_remote)[:5]:
             print(f"  - {f}")

if __name__ == "__main__":
    main()
