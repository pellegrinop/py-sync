# FTP File Sync with Conflict Resolution

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![lftp](https://img.shields.io/badge/dependency-lftp-orange.svg)](https://lftp.yar.ru/)

A robust Python-based file synchronization tool that automatically uploads local file changes to an FTP server with intelligent conflict resolution capabilities. Perfect for web developers and automated deployment workflows.

---

## Features

- **Real-time Monitoring**: Automatically detects and uploads file changes using `watchdog` filesystem events.
- **Smart Conflict Resolution**: Content-based detection that only triggers when files actually differ.
- **Session Memory**: Remembers your conflict choices (like "Always Override") for the current session to minimize prompts.
- **Intelligent Directory Handling**: Automatically creates remote directories (recursive `mkdir -p`) if they don't exist.
- **File Difference Viewer**: Integrated unified diff viewer to see exactly what's changing between local and remote.
- **Multiple Resolution Options**: Choose to override remote, download remote, skip, or save as a separate copy.
- **Flexible Configuration**: Externalized FTP credentials and path settings via JSON.
- **Ignore Patterns**: Support for shell-style globs and directory-prefix matching.

---

## System Requirements

- **Python**: 3.6+
- **System Dependencies**: `lftp` (The swiss army knife of FTP clients).
- **Operating System**: 
  - **Linux/macOS**: Native support.
  - **Windows**: Install `lftp` via **WSL2** (recommended), **Cygwin**, or **MSYS2**.

---

## Installation

### 1. Install `lftp`

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install lftp
```

**macOS (Homebrew):**
```bash
brew install lftp
```

**Windows (WSL):**
```bash
sudo apt-get install lftp
```

### 2. Setup Python Environment

```bash
# Create and activate virtual environment
python -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure

Create a `sync_config.json` file in the root directory (use `config.example.json` as a template):

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
  },
  "ignore": [
    "node_modules/",
    "*.tmp",
    ".git/",
    "*.log",
    "build/"
  ]
}
```

---

## Usage

### Standard Mode (Auto-upload)
Monitors files and uploads changes immediately.
```bash
python sync.py
```

### Interactive Conflict Mode
Checks for remote differences before uploading and prompts for resolution if they exist.
```bash
python sync.py --check-conflicts
# or
python sync.py -c
```

### Help
```bash
python sync.py --help
```

---

## How Conflict Resolution Works

When `--check-conflicts` is enabled:
1. **Detection**: The tool downloads a temporary copy of the remote file to compare content.
2. **Comparison**: If the content is identical, it skips the upload (saving bandwidth).
3. **Prompt**: If different, it shows a **unified diff** and asks:
   - **1. Override remote**: Upload your local changes (and remember this for the session).
   - **2. Override local**: Replace your local file with the server's version.
   - **3. Cancel**: Skip this file for now.
   - **4. Download copy**: Save the remote version as `filename_remote.ext`.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

---
*Built with care for developers who still use FTP.*
