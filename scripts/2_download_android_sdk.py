import os, sys, platform, zipfile, hashlib, shutil, subprocess, argparse
from pathlib import Path
from urllib.request import urlretrieve

ANDROID_COMMAND_LINE_TOOLS_VERSION = "13114758"
ANDROID_COMMAND_LINE_TOOLS_ZIP_SHA256 = ""

def sha256sum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha1sum(filepath):
    sha1 = hashlib.sha1()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha1.update(chunk)
    return sha1.hexdigest()


def download_android_command_line_tools(root):
    """
    Downloads the Android Command Line Tools.
    """
    ANDROID_COMMAND_LINE_TOOLS_VERSION = "13114758"
    system = platform.system()
    if system == 'Windows':
        ANDROID_COMMAND_LINE_TOOLS_HOST_OS = 'win'
        ANDROID_COMMAND_LINE_TOOLS_ZIP_SHA256 = "98b565cb657b012dae6794cefc0f66ae1efb4690c699b78a614b4a6a3505b003"
    elif system == 'Darwin':
        ANDROID_COMMAND_LINE_TOOLS_HOST_OS = 'mac'
        ANDROID_COMMAND_LINE_TOOLS_ZIP_SHA256 = "5673201e6f3869f418eeed3b5cb6c4be7401502bd0aae1b12a29d164d647a54e"
    elif system == 'Linux':
        ANDROID_COMMAND_LINE_TOOLS_HOST_OS = 'linux'
        ANDROID_COMMAND_LINE_TOOLS_ZIP_SHA256 = "7ec965280a073311c339e571cd5de778b9975026cfcbe79f2b1cdcb1e15317ee"
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

    url = f"https://dl.google.com/android/repository/commandlinetools-{ANDROID_COMMAND_LINE_TOOLS_HOST_OS}-{ANDROID_COMMAND_LINE_TOOLS_VERSION}_latest.zip"
    local_path = os.path.join(root, "_deps/android_commandlinetools.zip")
    if os.path.isfile(local_path) and sha256sum(local_path) == ANDROID_COMMAND_LINE_TOOLS_ZIP_SHA256:
        print("Android Command Line Tools already downloaded and verified.")
        return local_path
    
    print("Downloading Android Command Line Tools...")
    try:
        if not os.path.exists(os.path.join(root, "_deps")):
            os.makedirs(os.path.join(root, "_deps"))
        response = urlretrieve(url, os.path.join(root, "_deps/android_commandlinetools.zip"))
        print(f"Downloaded Android Command Line Tools to {response[0]}")
        if sha256sum(response[0]) != ANDROID_COMMAND_LINE_TOOLS_ZIP_SHA256:
            print("Downloaded file checksum does not match expected value.")
            sys.exit(1)
        return response[0]
    except Exception as e:
        print(f"Failed to download Android Command Line Tools: {e}")
        sys.exit(1)

    # Unzip the downloaded file
    with zipfile.ZipFile(os.path.join(root, "_deps/android_commandlinetools.zip"), 'r') as zip_ref:
        zip_ref.extractall(os.path.join(root, "_deps/android_commandlinetools"))
    print("Android Command Line Tools downloaded and extracted successfully.")  

    # Clean up the zip file
    os.remove(os.path.join(root, "_deps/android_commandlinetools.zip"))


def ensure_android_command_line_tools(root):
    """
    Ensure that the Android Command Line Tools are downloaded and extracted.
    """
    
    system = platform.system()
    if system == 'Windows':
        ANDROID_SDKMANAGER_SHA1 = "9a61ae445d2f51660ac889524ca136edf214a7f2"
        ANDROID_SDKMANAGER_FILENAME = "sdkmanager.bat"
    elif system == 'Darwin':
        ANDROID_SDKMANAGER_SHA1 = "188080972337a2d2e081dea295aab5e18d41c344"
        ANDROID_SDKMANAGER_FILENAME = "sdkmanager"
    elif system == 'Linux':
        ANDROID_SDKMANAGER_SHA1 = "c6b839ca0a64905e9d5e954e0d3589493b88d6de"
        ANDROID_SDKMANAGER_FILENAME = "sdkmanager"
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

    local_path = download_android_command_line_tools(root)
    cmdline_base_path = os.path.join(root, "_deps/android-cmdline-tools")
    cmdline_path = os.path.join(cmdline_base_path, "cmdline-tools")
    sdkmanager_path = os.path.join(cmdline_path, "bin", ANDROID_SDKMANAGER_FILENAME)

    if os.path.isfile(sdkmanager_path) and sha1sum(sdkmanager_path) == ANDROID_SDKMANAGER_SHA1:
        print("Android SDK Manager is already installed and verified.")
        return sdkmanager_path

    if os.path.exists(cmdline_path):
        print(f"Removing existing broken cmdline-tools directory at {cmdline_path}")
        shutil.rmtree(cmdline_path)
    elif not os.path.exists(cmdline_base_path):
        print(f"Creating directory for Android Command Line Tools at {cmdline_base_path}")
        os.makedirs(cmdline_base_path)

    print("Extracting Android Command Line Tools...")
    with zipfile.ZipFile(local_path, 'r') as zip_ref:
        zip_ref.extractall(cmdline_base_path)
    print("Android Command Line Tools extracted successfully.")
    return sdkmanager_path


def install_android_sdk_tools(root):
    """
    Install the Android SDK tools.
    """
    sdkmanager = ensure_android_command_line_tools(root)
    sdk_path = os.path.join(root, '_deps/android-sdk')
    os.makedirs(sdk_path, exist_ok=True)
    
    subprocess.run([
        os.path.normpath(sdkmanager), 
        "--install", 
        "platform-tools", 
        "platforms;android-22", 
        "build-tools;22.0.1", 
        "ndk;27.2.12479018",
        f"--sdk_root={sdk_path}",
        ], check=True)
    
    print("Android SDK components installed successfully.")
    print("Android Command Line Tools are ready to use.")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="2_download_android_sdk", 
        description="Ensure Android SDK tools are downloaded and installed."
    )

    # Positional argument "path"
    parser.add_argument(
        "root",
        type=Path,
        metavar="root",
        help="root directory of onnxruntime-secure repository"
    )

    # Parse arguments; will auto-exit and print usage on error
    args = parser.parse_args()
    root = args.root.resolve()

    install_android_sdk_tools(root)