
import os
import paramiko
import sys
from pathlib import Path
import stat

# --- CONFIGURATION ---
HOST = "sol.dil.univ-mrs.fr"
PORT = 22
USERNAME = "chevallier"
PASSWORD = "39che67$$+"
REMOTE_TARGET_DIR = "/space/home/chevallier/InterroPedago/data"
LOCAL_DATA_DIR = Path(__file__).parent / "data"

def create_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD)
    return client

def get_remote_file_map(ssh):
    """
    Get all remote files and their sizes in one command.
    Returns: dict { 'relative/path': size_int }
    """
    print("⚡ Fetching remote file list (Fast Mode)...")
    
    # Use 'find' to list all files with size
    # %P = File's name relative to starting point? No, %P is available in recent find.
    # If standard find, we might need acdptation.
    # Let's try standard format.
    cmd = f"find {REMOTE_TARGET_DIR} -type f -printf '%P\t%s\n'"
    
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    remote_map = {}
    
    for line in stdout:
        parts = line.strip().split('\t')
        if len(parts) == 2:
            rel_path, size = parts
            remote_map[rel_path] = int(size)
            
    err = stderr.read().decode()
    if err and "find: " in err: # Ignore minor permissions warnings if any
        print(f"Server Warning: {err.strip()}")
        
    print(f"✅ Found {len(remote_map)} files remotely.")
    return remote_map

def sync(ssh, sftp, remote_map, local_dir):
    # Iterate local
    if not local_dir.exists():
        return

    # Use os.walk for efficiency local side too
    for root, dirs, files in os.walk(local_dir):
        # Excludes
        if "temp" in dirs: dirs.remove("temp")
        if "__pycache__" in dirs: dirs.remove("__pycache__")
        
        # PRIORITIZE: Sort files? 
        # os.walk yields random order often.
        # But global logic is handled by "Map first, then upload".
        
        rel_root = Path(root).relative_to(local_dir)
        
        for name in files:
            if name.startswith("."): continue
            
            local_path = Path(root) / name
            rel_path_obj = rel_root / name
            rel_path_str = str(rel_path_obj)
            
            remote_path_abs = f"{REMOTE_TARGET_DIR}/{rel_path_str}"
            
            local_size = local_path.stat().st_size
            
            should_upload = False
            
            if rel_path_str in remote_map:
                if remote_map[rel_path_str] == local_size:
                    # Same logic
                    should_upload = False
                else:
                    print(f"🔄 Updating {rel_path_str} (Diff)")
                    should_upload = True
            else:
                print(f"🚀 Uploading {rel_path_str}")
                should_upload = True
                
            if should_upload:
                # Ensure parent directory exists?
                # SFTP put requires dir. 'find' map only gives files.
                # We might need to mkdir -p. 
                # Optimization: Keep a cache of created dirs? 
                # Or just try-except? Or just mkdir -p via SSH?
                parent_dir = str(Path(remote_path_abs).parent)
                # Quick check logic or blindly create?
                # Blind creation via SSH is fast: mkdir -p
                try:
                    _, stdout, _ = ssh.exec_command(f"mkdir -p \"{parent_dir}\"") # Blocking?
                    stdout.read() # Force wait and close channel
                    # sftp put
                    sftp.put(str(local_path), remote_path_abs)
                    print(f"✅ Sent {rel_path_str}")
                except Exception as e:
                    print(f"❌ Error uploading {rel_path_str}: {e}")

    # DELETION LOGIC ? User: "Peut-on supprimer?" -> Yes we implemented it.
    # Verify: remote_map contains ALL remote files.
    # We iterate LOCAL files. We can track "visited".
    # Remaining in remote_map are orphans.
    
    # Let's re-implement checking of orphans
    # But wait, os.walk structure above logic is slightly inverted for full orphan check efficiently.
    # Let's collect local relative paths first
    pass # Refactor follows in main execution

def main():
    print(f"🚀 Starting Optimized Sync to {HOST}...")
    
    try:
        ssh = create_client()
        sftp = ssh.open_sftp()
        
        # 1. Get snapshot of remote state
        try:
            # Ensure root exists first
            sftp.mkdir(REMOTE_TARGET_DIR) 
        except: 
            pass # Exists
            
        remote_map = get_remote_file_map(ssh) # {'path': size}
        
        # Copy for orphan tracking
        remaining_remote = set(remote_map.keys())
        
        # 2. Walk Local
        for root, dirs, files in os.walk(LOCAL_DATA_DIR):
            if "temp" in dirs: dirs.remove("temp")
            if "__pycache__" in dirs: dirs.remove("__pycache__")
            
            # SORT dirs (courses, global, then students)
            # os.walk names: we can sort inplace
            dirs.sort(key=lambda x: (x != "courses", x != "global", x))
            
            rel_root = Path(root).relative_to(LOCAL_DATA_DIR)
            
            for file in sorted(files):
                if file.startswith("."): continue
                
                local_path = Path(root) / file
                rel_path_str = str(rel_root / file)
                
                # Check Size
                local_size = local_path.stat().st_size
                should_upload = True
                
                if rel_path_str in remote_map:
                    remaining_remote.discard(rel_path_str) # Mark visited
                    if remote_map[rel_path_str] == local_size:
                        should_upload = False
                    else:
                        print(f"🔄 Updating {rel_path_str}")
                else:
                    print(f"🚀 Uploading {rel_path_str}")
                
                if should_upload:
                    remote_full = f"{REMOTE_TARGET_DIR}/{rel_path_str}"
                    # Ensure dir
                    parent_full = str(Path(remote_full).parent)
                    _, stdout, _ = ssh.exec_command(f"mkdir -p \"{parent_full}\"")
                    stdout.read() # Close channel
                    
                    sftp.put(str(local_path), remote_full)
                    print(f"✅ Sent {rel_path_str}")

        # 3. Handle Deletions
        for orphan in remaining_remote:
            full_orphan = f"{REMOTE_TARGET_DIR}/{orphan}"
            print(f"🗑️ Deleting orphan: {orphan}")
            try:
                sftp.remove(full_orphan)
            except Exception as e:
                print(f"Error delete {orphan}: {e}")

        sftp.close()
        print("\n✨ Sync Complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        try: ssh.close()
        except: pass

if __name__ == "__main__":
    main()
