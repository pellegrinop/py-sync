# FTP File Sync with Conflict Resolution

A Python-based file synchronization tool that automatically uploads local file changes to an FTP server with intelligent conflict resolution capabilities.

## 🚀 Features

- **Real-time File Monitoring**: Automatically detects and uploads file changes using filesystem events
- **Smart Conflict Resolution**: Content-based conflict detection with session memory
- **Session Override Memory**: Remember your conflict choices for the current session
- **Intelligent Directory Handling**: Automatically creates remote directories if they don't exist
- **File Difference Viewer**: Shows unified diffs between local and remote files when conflicts occur
- **Multiple Resolution Options**: Override, download, skip, or save remote copies when conflicts arise
- **Secure Configuration**: Externalized FTP credentials and paths via JSON configuration

## 📋 System Requirements

- **Operating System**: Linux (tested on Ubuntu, compatible with most distributions)
- **Python**: 3.6+ (uses f-strings and modern pathlib features)
- **System Dependencies**: `lftp` package for FTP operations

## 🔧 Installation

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install lftp python3 python3-pip python3-venv
```

### 2. Create and Activate Virtual Environment

```bash
python3 -m venv ~/ftp-sync-env
source ~/ftp-sync-env/bin/activate
```

### 3. Install Python Dependencies

```bash
pip3 install watchdog
```

### 4. Configure the Application

Create a `config.json` file in the same directory as `sync.py`:

```json
{
  "ftp": {
    "host": "your.ftp.server.com",
    "port": "21",
    "user": "your_username",
    "password": "your_password"
  },
  "directories": {
    "remote": "/path/to/remote/directory/",
    "local": "/path/to/local/directory/"
  }
   ,
   "ignore": [
      "node_modules/",
      "*.tmp",
      "build/"
   ]
}
```

**Note**: Use `config.example.json` as a template for your configuration.

### 5. Verify Installation

```bash
lftp --version        # Should display lftp version information
python3 --version     # Should show Python 3.6 or higher
```

## 🚦 Usage

### Basic Mode (Auto-upload)

Automatically uploads any local file changes without conflict checking:

```bash
source ~/ftp-sync-env/bin/activate
python3 ./sync.py
```

### Conflict Resolution Mode

Enables conflict detection and interactive resolution:

```bash
python3 ./sync.py --check-conflicts
# or
python3 ./sync.py -c
```

### Help

Display usage information:

```bash
python3 ./sync.py -h
```

## 🔄 Smart Conflict Resolution

The tool uses **content-based conflict detection** - it only triggers when remote files exist and have different content than your local files.

### Conflict Resolution Options

When conflicts are detected, you'll be presented with these options:

1. **Override remote file (remember for session)** - Upload your local version and remember this choice
2. **Override local file** - Download the remote version  
3. **Cancel and handle manually** - Skip this file for manual resolution
4. **Download a copy** - Save remote version as `filename_remote.ext` and proceed with upload

### Session Memory

- **Choose "Override" (option 1)**: The tool remembers your choice for this file during the current session
- **Subsequent changes**: Automatically uploads without asking again
- **Restart program**: Asks again (fresh session)
- **Other choices**: Always asks every time

This approach is perfect for development workflows where you make multiple edits to the same files.

## 📁 File Structure

```
python_sync/
├── sync.py              # Main synchronization script
├── config.json          # Your FTP configuration (create from example)
├── config.example.json  # Configuration template
└── README.md           # This file
```

## ⚙️ Configuration Details

### FTP Settings
- `host`: FTP server hostname or IP address
- `port`: FTP server port (usually 21)
- `user`: FTP username
- `password`: FTP password

### Directory Settings
- `remote`: Absolute path to the remote directory on the FTP server
- `local`: Absolute path to the local directory to monitor

### Ignore patterns
- `ignore`: Optional list of patterns to skip files or folders during processing. Patterns support shell-style globs (via `fnmatch`) and absolute paths.
- If you want to ignore a folder, the pattern must end with a trailing slash (`/`). For example, to ignore `node_modules` and any of its contents, use `"node_modules/"`.
- File patterns like `"*.tmp"` will match files by name.

Examples:

```json
"ignore": [
   "node_modules/",   # ignore the node_modules folder and everything under it
   "build/",          # ignore build folder
   "*.tmp",           # ignore all .tmp files
   "/absolute/path/to/ignore/"  # ignore a specific absolute folder path
]
```

Notes:
- Directory patterns must end with `/` to be treated as folder-prefix matches.
- Patterns are matched against the relative path (normalized to use `/`) and against filenames. Absolute path patterns are also supported.

## 🛡️ Security Considerations

- Keep your `config.json` file secure and never commit it to version control
- Consider using environment variables for sensitive credentials in production
- The `config.example.json` file is safe to share as it contains only placeholders

## 🐛 Troubleshooting

### Common Issues

1. **"Configuration file not found"**
   - Ensure `config.json` exists in the same directory as `sync.py`
   - Verify the file is properly formatted JSON

2. **"Upload failed"**
   - Check FTP credentials and connectivity
   - Verify remote directory permissions
   - Ensure `lftp` is installed and accessible

3. **"Cannot show diff for binary file"**
   - This is normal for binary files (images, executables, etc.)
   - Conflict resolution will still work, but diffs won't be displayed

4. **Conflicts not being detected**
   - Ensure you're using `--check-conflicts` flag
   - Verify the remote file actually exists and differs from local
   - Check FTP server connectivity

5. **Session overrides not working**
   - Session memory only lasts while the program is running
   - Restart the program to reset all override choices
   - Only "Override remote file" (option 1) is remembered

### Dependency Verification

```bash
# Check if lftp is installed
which lftp

# Verify Python packages
pip list | grep watchdog
```

### Connection test at startup

- The script now performs a quick FTP connection test at startup using `lftp` and will exit early if the connection fails.
- On failure the program prints `lftp`'s stdout and stderr so you can see the exact FTP error (authentication, permissions, host not found, etc.).
- If `lftp` is not available, you'll see a clear message asking you to install it.

This helps surface the real reason a connection to the FTP server cannot be established so you can fix credentials or network issues before the watcher starts.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is provided as-is. Please review and modify according to your needs.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Verify your configuration and dependencies
3. Test with a simple file change to isolate the issue
