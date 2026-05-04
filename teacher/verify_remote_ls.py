
import paramiko
import stat

HOST = "sol.dil.univ-mrs.fr"
PORT = 22
USERNAME = "chevallier"
PASSWORD = "39che67$$+"
REMOTE_TARGET_DIR = "/space/home/chevallier/InterroPedago/data"

def main():
    print(f"🕵️ Checking remote content at {REMOTE_TARGET_DIR}...")
    try:
        transport = paramiko.Transport((HOST, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        files = sftp.listdir(REMOTE_TARGET_DIR)
        print("📁 Remote 'data' content:")
        for f in files:
            print(f" - {f}")
            
        sftp.close()
        transport.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
