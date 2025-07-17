import sys, platform, os, argparse, re
from pathlib import Path
import subprocess
from dataclasses import make_dataclass, fields


def flatten(seq):
    out = []
    for e in seq:
        if isinstance(e, list):
            out += flatten(e)
        else:
            out.append(e)
    return out

def build(root, options, cmake_options):
    src_path = (root / "_deps" / "onnxruntime-src").resolve().absolute()
    build_script = src_path / "build.bat" if platform.system() == 'Windows' else src_path / "build.sh"
    build_script = build_script.resolve().absolute()
    options = [str(os.path.abspath(x)) if isinstance(x, os.PathLike) else x
               for x in flatten(options)]
    options += ['--cmake_extra_defines'] \
        + [f'{k}={str(os.path.abspath(v)) if isinstance(v, os.PathLike) else v}' 
           for k, v in cmake_options.items()]
    return subprocess.run([str(build_script)] + options, check=True)


if __name__ == "__main__":
    """
    Ensure the Android repository is cloned and updated.
    """

    parser = argparse.ArgumentParser(
        prog="3_install_onnxruntime_linux",
        description="Build and install onnxruntime for Linux"
    )
    parser.add_argument(
        "root",
        type=Path,
        metavar="root",
        help="root directory of onnxruntime-secure repository"
    )
    parser.add_argument(
        "--build_shared_lib",
        help="enable shared library build",
        action="store_true"
    )

    args = parser.parse_args()
    root = args.root.resolve().absolute()
    src_path = root / "_deps" / "onnxruntime-src"
    build_path = root / "_deps" / "onnxruntime-build" / "Linux"
    install_path = root / "_deps" / "onnxruntime-install" / "Linux"

    base_options = [
        '--config', 'Release', 
        '--cmake_generator', 'Ninja',
        '--parallel',
        '--compile_no_warning_as_error',
        '--skip_submodule_sync',
        '--skip_tests',
    ]

    if args.build_shared_lib:
        base_options.append('--build_shared_lib')
        build_path = build_path / 'shared'
        install_path = install_path / 'shared'
    else:
        build_path = build_path / 'static'
        install_path = install_path / 'static'

    print(f"Building ONNX Runtime for Linux...")
    options = base_options + [
        '--build_dir', build_path,
        '--target', 'install',
    ]
    cmake_options = {
        "CMAKE_INSTALL_PREFIX": install_path,
    }
       
    result = build(
        root, 
        options,
        cmake_options
        )
    if result.returncode != 0:
        print(f"Failed to build ONNX Runtime for Linux.")
        sys.exit(result.returncode)
    else:
        print(f"ONNX Runtime built and installed to {str(install_path)}")
