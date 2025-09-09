from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import time
import os
import argparse
import tempfile
import difflib
import json
import fnmatch

def load_config(config_path="sync_config.json"):
    """Load configuration from external JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"❌ Configuration file '{config_path}' not found!")
        print("Please create a config.json file with your FTP settings.")
        print("See documentation in the script for the required format.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing configuration file: {e}")
        exit(1)

# Load configuration
CONFIG = load_config()
FTP_HOST = CONFIG['ftp']['host']
FTP_PORT = CONFIG['ftp']['port']
FTP_USER = CONFIG['ftp']['user']
FTP_PASS = CONFIG['ftp']['password']
REMOTE_DIR = CONFIG['directories']['remote']
LOCAL_DIR = CONFIG['directories']['local']

# Load ignore patterns from config
IGNORE_PATTERNS = []
cfg_ignore = CONFIG['ignore'] if 'ignore' in CONFIG else []
if isinstance(cfg_ignore, list):
    IGNORE_PATTERNS.extend([p.strip() for p in cfg_ignore if p.strip()])

if IGNORE_PATTERNS:
    print(f"Loaded ignore patterns: {IGNORE_PATTERNS}")


def test_ftp_connection(timeout=15):
    "Test FTP connection using lftp."
    
    test_cmd = f"""
    set net:max-retries 2;
    set net:timeout {timeout};
    ls {REMOTE_DIR};
    bye
    """
    try:
        result = subprocess.run([
            "lftp", "-u", f"{FTP_USER},{FTP_PASS}", "-p", FTP_PORT, FTP_HOST,
            "-e", test_cmd
        ], capture_output=True, text=True, timeout=timeout + 5)
    except FileNotFoundError:
        print("❌ 'lftp' command not found. Please install 'lftp' and ensure it's in PATH.")
        exit(1)
    except subprocess.TimeoutExpired:
        print(f"❌ FTP connection timed out after {timeout} seconds when contacting {FTP_HOST}:{FTP_PORT}")
        exit(1)

    if result.returncode != 0:
        print(f"❌ FTP connection test failed (return code {result.returncode}).")
        if result.stdout:
            print("--- lftp stdout ---")
            print(result.stdout.strip())
        if result.stderr:
            print("--- lftp stderr ---")
            print(result.stderr.strip())
        exit(1)
    else:
        print(f"✅ FTP connection to {FTP_HOST}:{FTP_PORT} OK. Remote dir: {REMOTE_DIR}")

class FTPUploader(FileSystemEventHandler):
    def __init__(self, check_conflicts=False):
        self.check_conflicts = check_conflicts
        self.session_overrides = {}  # Track files we've chosen to always override this session

    def is_ignored(self, rel_path, filename, abs_path):
        """Return True if the path or filename matches any ignore pattern."""
        if not IGNORE_PATTERNS:
            return False

        # Normalize to forward slashes for pattern matching
        rel_path_unified = rel_path.replace(os.sep, '/')

        for pat in IGNORE_PATTERNS:
            if not pat:
                continue
            pat = pat.strip()
            # treat directory patterns ending with '/' as prefix match
            if pat.endswith('/'):
                prefix = pat.rstrip('/')
                if rel_path_unified == prefix or rel_path_unified.startswith(prefix + '/'):
                    return True
            # fnmatch against relative path and filename
            if fnmatch.fnmatch(rel_path_unified, pat) or fnmatch.fnmatch(filename, pat):
                return True
            # absolute path pattern
            try:
                if os.path.isabs(pat) and abs_path.startswith(pat):
                    return True
            except Exception:
                pass
        return False
    
    def remote_file_exists(self, remote_path, filename):
        """Check if remote file exists"""
        info_cmd = f"""
        cd {remote_path};
        ls;
        bye
        """
        
        result = subprocess.run([
            "lftp", "-u", f"{FTP_USER},{FTP_PASS}", "-p", FTP_PORT, FTP_HOST,
            "-e", info_cmd
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if filename in line:
                    return True
        
        return False
    
    def files_are_identical(self, local_path, remote_temp_path):
        """Compare two files to check if they are identical"""
        try:
            with open(local_path, 'rb') as f1, open(remote_temp_path, 'rb') as f2:
                return f1.read() == f2.read()
        except Exception as e:
            print(f"Error comparing files: {e}")
            return False
    
    def download_remote_file(self, remote_path, filename, local_file_path):
        """Download remote file content for comparison"""
        # Create a temporary filename in the same directory as the local file
        local_dir = os.path.dirname(local_file_path)
        name, ext = os.path.splitext(filename)
        temp_filename = f"{name}_remote_temp{ext}"
        temp_path = os.path.join(local_dir, temp_filename)
        
        download_cmd = f"""
        set xfer:clobber on;
        cd {remote_path};
        get {filename} -o {temp_path};
        bye
        """
        
        result = subprocess.run([
            "lftp", "-u", f"{FTP_USER},{FTP_PASS}", "-p", FTP_PORT, FTP_HOST,
            "-e", download_cmd
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(temp_path) and os.path.getsize(temp_path) >= 0:
                return temp_path
            else:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    
    def show_file_diff(self, local_path, remote_temp_path, filename):
        """Show differences between local and remote files"""
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                local_content = f.readlines()
        except UnicodeDecodeError:
            print(f"Cannot show diff for binary file: {filename}")
            return
        
        try:
            with open(remote_temp_path, 'r', encoding='utf-8') as f:
                remote_content = f.readlines()
        except UnicodeDecodeError:
            print(f"Cannot show diff for binary file: {filename}")
            return
        
        print(f"\n=== DIFFERENCES for {filename} ===")
        diff = difflib.unified_diff(
            remote_content, local_content,
            fromfile=f"Remote: {filename}",
            tofile=f"Local: {filename}",
            lineterm=''
        )
        
        diff_lines = list(diff)
        if not diff_lines:
            print("Files are identical in content.")
        else:
            for line in diff_lines:
                print(line)
        print("=" * 50)
    
    def resolve_conflict(self, local_path, remote_path, filename):
        """Handle file conflict resolution with session-based override tracking"""
        print(f"\n🔄 CONFLICT DETECTED for {filename}")
        
        # Download remote file for comparison
        remote_temp_path = self.download_remote_file(remote_path, filename, local_path)
        if remote_temp_path:
            self.show_file_diff(local_path, remote_temp_path, filename)
        
        while True:
            print(f"\nChoose action for {filename}:")
            print("1. Override remote file (upload local) - remember for session")
            print("2. Override local file (download remote)")
            print("3. Cancel and handle manually")
            print("4. Download a copy (save remote as *_remote.*)")
            
            choice = input("Enter choice (1/2/3/4): ").strip()
            
            if choice == "1":
                # Upload local file and remember this choice for the session
                self.session_overrides[filename] = True
                print(f"📝 Will always override {filename} for this session")
                if remote_temp_path:
                    os.unlink(remote_temp_path)
                return "upload"
            elif choice == "2":
                # Download remote file
                if remote_temp_path:
                    # Replace local file with remote content
                    os.replace(remote_temp_path, local_path)
                    print(f"✅ Local file updated with remote content: {filename}")
                return "download"
            elif choice == "3":
                # Cancel
                if remote_temp_path:
                    os.unlink(remote_temp_path)
                print(f"⏭️  Skipping {filename} - handle manually")
                return "cancel"
            elif choice == "4":
                # Download copy with _remote suffix
                if remote_temp_path:
                    # Create filename with _remote suffix while preserving extension
                    name, ext = os.path.splitext(filename)
                    remote_copy_name = f"{name}_remote{ext}"
                    local_dir = os.path.dirname(local_path)
                    remote_copy_path = os.path.join(local_dir, remote_copy_name)
                    
                    # Copy the remote file to the new location
                    os.replace(remote_temp_path, remote_copy_path)
                    print(f"📥 Remote copy saved as: {remote_copy_name}")
                return "copy"
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")

    def on_modified(self, event):
        if event.is_directory:
            return

        # Skip temporary files created by our own conflict resolution
        filename = os.path.basename(event.src_path)
        if "_remote_temp" in filename:
            return

        rel_path = os.path.relpath(event.src_path, LOCAL_DIR)
        rel_dir = os.path.dirname(rel_path)
        if rel_dir:
            remote_path = os.path.join(REMOTE_DIR, rel_dir).replace("\\", "/")
        else:
            remote_path = REMOTE_DIR.rstrip("/")
        filename = os.path.basename(event.src_path)

        # If the path matches ignore patterns, skip processing
        if self.is_ignored(rel_path, filename, event.src_path):
            print(f"Skipping ignored path: {rel_path}")
            return

        print(f"Processing: {rel_path} → {remote_path}/{filename}")

        # Check for conflicts if enabled
        if self.check_conflicts:
            # Check if we've already decided to always override this file this session
            if filename in self.session_overrides:
                print(f"🔄 Auto-overriding {filename} (session choice)")
                # Continue to upload section
            elif self.remote_file_exists(remote_path, filename):
                # Remote file exists, check if content is different
                print(f"📁 Remote file exists. Downloading to check for differences...")
                remote_temp_path = self.download_remote_file(remote_path, filename, event.src_path)
                if remote_temp_path:
                    # Compare files to see if they're actually different
                    if self.files_are_identical(event.src_path, remote_temp_path):
                        print(f"✅ Files are identical, no conflict. Skipping upload for: {filename}")
                        os.unlink(remote_temp_path)
                        return
                    else:
                        # Files are different, trigger conflict resolution
                        print(f"🔄 Files differ. Resolving conflict...")
                        os.unlink(remote_temp_path)  # Clean up temp file
                        action = self.resolve_conflict(event.src_path, remote_path, filename)
                        if action == "cancel":
                            return
                        elif action == "download":
                            # File was already downloaded in resolve_conflict
                            return
                        elif action == "copy":
                            # Remote copy was saved, now proceed with upload of local file
                            print(f"Remote copy saved. Now uploading local version...")
                            # Continue to upload section
                else:
                    print(f"Failed to download remote file for comparison. Proceeding with upload...")
            else:
                print(f"No remote file found. Proceeding with upload...")

        # Proceed with upload (either no conflict check, no remote file, or user chose to upload)
        print(f"Uploading: {filename}")
        
        # First, try to upload the file directly
        upload_cmd = f"""
        cd {remote_path};
        put {event.src_path};
        bye
        """

        result = subprocess.run([
            "lftp", "-u", f"{FTP_USER},{FTP_PASS}", "-p", FTP_PORT, FTP_HOST,
            "-e", upload_cmd
        ], capture_output=True, text=True)

        # If upload failed, check if it's due to missing directory
        if result.returncode != 0:
            print(f"Upload failed, creating directory and retrying...")
            create_and_upload_cmd = f"""
            mkdir -p {remote_path};
            cd {remote_path};
            put {event.src_path};
            bye
            """
            
            retry_result = subprocess.run([
                "lftp", "-u", f"{FTP_USER},{FTP_PASS}", "-p", FTP_PORT, FTP_HOST,
                "-e", create_and_upload_cmd
            ], capture_output=True, text=True)

            if retry_result.returncode == 0:
                print(f"✅ Successfully uploaded after creating directory: {filename}")
            else:
                print(f"❌ Failed to upload {filename}: {retry_result.stderr}")
        else:
            print(f"✅ Successfully uploaded: {filename}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='FTP File Sync with Conflict Resolution')
    parser.add_argument('--check-conflicts', '-c', action='store_true',
                       help='Enable conflict resolution mode. When enabled, checks if remote files exist and shows differences before uploading.')
    args = parser.parse_args()
    
    test_ftp_connection()
    
    event_handler = FTPUploader(check_conflicts=args.check_conflicts)
    observer = Observer()
    observer.schedule(event_handler, LOCAL_DIR, recursive=True)
    observer.start()
    
    if args.check_conflicts:
        print("🔍 FTP sync started with conflict resolution enabled. Press Ctrl+C to stop.")
        print("   When conflicts are detected, you'll be prompted to resolve them.")
    else:
        print("📁 FTP sync started (standard mode). Press Ctrl+C to stop.")
        print("   Use --check-conflicts to enable conflict resolution.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
