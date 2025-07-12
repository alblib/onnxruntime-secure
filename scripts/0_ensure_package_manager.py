#!/usr/bin/env python3
import sys
import os
import platform
import subprocess

def is_windows_version_supported():
    # On Windows, platform.release() returns e.g. "10", "11"
    try:
        ver = platform.release()
        return int(ver) >= 10
    except ValueError:
        return False

def ensure_winget():
    try:
        subprocess.run(['winget', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("winget not found. Attempting to install winget…")
        # Download the MSIX bundle
        installer_url = 'https://aka.ms/getwinget'
        tmpfile = os.path.join(os.environ.get('TEMP', '/tmp'), 'getwinget.msixbundle')
        try:
            subprocess.run([
                'powershell', '-Command',
                f"Invoke-WebRequest -Uri {installer_url!r} -OutFile {tmpfile!r}"
            ], check=True)
            subprocess.run([
                'powershell', '-Command',
                f"Add-AppxPackage -Path {tmpfile!r}"
            ], check=True)
            print("winget installed successfully.")
        except subprocess.CalledProcessError:
            print("Failed to install winget. Please install the Windows Package Manager manually:")
            print("https://learn.microsoft.com/windows/package-manager/winget/")
            sys.exit(1)

def is_ubuntu_version_supported():
    # Parse /etc/os-release for ID and VERSION_ID
    try:
        info = {}
        with open('/etc/os-release') as f:
            for line in f:
                if '=' in line:
                    k,v = line.rstrip().split('=',1)
                    info[k] = v.strip('"')
        if info.get('ID','') != 'ubuntu':
            return False
        # Compare version strings "22.04" -> float 22.04
        return float(info.get('VERSION_ID','0')) >= 22.04
    except Exception:
        return False

def ensure_homebrew():
    try:
        subprocess.run(['brew', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Homebrew is installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Homebrew is not installed. Attempting to install Homebrew…")
        try:
            # Use the official Homebrew install script
            subprocess.run([
                'bash', '-c',
                '"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            ], check=True)
            print("Homebrew installed successfully.")
        except subprocess.CalledProcessError:
            print("Failed to install Homebrew. Please install it manually from https://brew.sh/")
            sys.exit(1)

def main():
    system = platform.system()
    if system == 'Windows':
        if not is_windows_version_supported():
            print("Unsupported Windows version. Windows 10 or later is required.")
            sys.exit(1)
        ensure_winget()
        print("Windows >=10 and winget OK.")
    elif system == 'Linux':
        if is_ubuntu_version_supported():
            print("Ubuntu >=22.04 detected.")
        else:
            print("Unsupported Linux distribution or version. Ubuntu 22.04 or later is required.")
            sys.exit(1)
    elif system == 'Darwin':
        ensure_homebrew()
        print("macOS detected and Homebrew installation OK.")
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

if __name__ == '__main__':
    main()
