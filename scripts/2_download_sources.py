import os, shutil, subprocess, argparse
from pathlib import Path

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
    run(["git", "fetch", "--all", "--tags"], cwd=clone_dir)
    run(["git", "reset", "--hard", "origin/main"], cwd=clone_dir)
    run(["git", "submodule", "update", "--init", "--recursive", "--force"], cwd=clone_dir)

def ensure_feature_repo(url, ref, root, feature_name):
    """
    Ensure the specified feature repository is cloned and updated.
    :param url: URL of the repository to clone.
    :param root: The onnxruntime-secure root directory.
    :param feature_name: The repository is cloned into '{root}/_deps/{feature_name}'.
    :return: Path to the cloned repository.
    """
    REPO_URL = url
    CLONE_DIR = os.path.join(root, "_deps", feature_name)

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

    checkout_ref(CLONE_DIR, ref)

    return CLONE_DIR


# helpers for checking out a tag or branch by name
def ref_exists(path, ref, namespace):
    """Return True if ref exists under refs/{namespace}/{ref}."""
    try:
        subprocess.run(
            ["git", "show-ref", "--verify", f"refs/{namespace}/{ref}"],
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

def checkout_ref(clone_dir, ref):
    """
    Checkout the given tag or branch in the repo:
      - If it's a tag → detached HEAD at that tag
      - If it's a remote branch → local tracking branch
    """
    # make sure we have all remotes/tags
    run(["git", "fetch", "--all", "--tags"], cwd=clone_dir)

    # 1) tag?
    if ref_exists(clone_dir, ref, "tags"):
        run(["git", "checkout", f"tags/{ref}"], cwd=clone_dir)
        # now sync submodules to the tag’s recorded commits
        run(["git", "submodule", "update", "--init", "--recursive", "--force"], cwd=clone_dir)
        return

    # 2) remote branch?
    if ref_exists(clone_dir, ref, "remotes/origin"):
        # if local branch exists already
        if ref_exists(clone_dir, ref, "heads"):
            run(["git", "checkout", ref], cwd=clone_dir)
        else:
            run(["git", "checkout", "-b", ref, f"origin/{ref}"], cwd=clone_dir)
        # and sync its submodules
        run(["git", "submodule", "update", "--init", "--recursive", "--force"], cwd=clone_dir)
        return


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="2_download_sources",
        description="Ensure source repositories for APIs are cloned and updated."
    )

    # Positional argument "path"
    parser.add_argument(
        "root",
        type=Path,
        metavar="root",
        help="root directory of onnxruntime-secure repository"
    )

    parser.add_argument(
        "features",
        nargs="+",                          # <-- require at least one
        choices=["opencl", "onnxruntime"],
        help="one or more features to enable"
    )

    # Parse arguments; will auto-exit and print usage on error
    args = parser.parse_args()
    root = args.root.resolve()

    if "opencl" in args.features:
        ensure_feature_repo(
            "https://github.com/KhronosGroup/OpenCL-SDK.git",
            "v2024.10.24",
            root, 
            "opencl-src"
            )
    if "onnxruntime" in args.features:
        ensure_feature_repo(
            "https://github.com/microsoft/onnxruntime.git",
            "v1.22.1",
            root,
            "onnxruntime-src"
        )
