import os
import shutil
import subprocess

def run(cmd, cwd=None):
    print(f"[RUN] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def get_remote_url(path):
    try:
        result = subprocess.run(["git", "config", "--get", "remote.origin.url"],
                                cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def clone_repo(repo_url, clone_dir):
    run(["git", "clone", "--recursive", repo_url, clone_dir])

def reset_and_update(clone_dir):
    run(["git", "fetch", "--all"], cwd=clone_dir)
    run(["git", "reset", "--hard", "origin/main"], cwd=clone_dir)
    run(["git", "submodule", "update", "--init", "--recursive", "--force"], cwd=clone_dir)

def ensure_opencl_src_repo(root):
    REPO_URL = "https://github.com/KhronosGroup/OpenCL-SDK.git"
    CLONE_DIR = os.path.join(root, "_deps", "opencl-src")

    if os.path.isdir(CLONE_DIR):
        if is_git_repo(CLONE_DIR):
            remote_url = get_remote_url(CLONE_DIR)
            if remote_url != REPO_URL:
                print("[-] Remote URL mismatch. Removing and recloning.")
                shutil.rmtree(CLONE_DIR)
                clone_repo(REPO_URL, CLONE_DIR)
            else:
                print("[+] Repository exists and is correct. Updating...")
                reset_and_update(CLONE_DIR)
        else:
            print("[-] Folder exists but is not a Git repository. Removing and recloning.")
            shutil.rmtree(CLONE_DIR)
            clone_repo(REPO_URL, CLONE_DIR)
    else:
        print("[+] Folder does not exist. Cloning repository.")
        os.makedirs(os.path.dirname(CLONE_DIR), exist_ok=True)
        clone_repo(REPO_URL, CLONE_DIR)

def build_opencl(root):
    print("[TODO] Add OpenCL build steps here.")
    pass

if __name__ == "__main__":
    root = os.path.abspath(".")
    ensure_opencl_src_repo(root)
    build_opencl(root)
