import sys, platform, os, argparse
from pathlib import Path
from enum import Enum
import subprocess

class Architecture(Enum):
    X86 = "--x86"
    X64 = ""
    ARM64 = "--arm64"
    ARM32 = "--arm"

class ExecutionProvider(Enum):
    DirectML = "--use_dml"
    CUDA = "--use_cuda"
    oneDNN = "--use_dnnl"
    NNAPI = "--use_nnapi"
    CoreML = "--use_coreml"

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
    build_script = src_path / "build.bat" if platform.system() == 'Windows' else src_path / "build"
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
        prog="3_install_onnxruntime_android",
        description="Build and install onnxruntime for Android"
    )

    parser.add_argument(
        "root",
        type=Path,
        metavar="root",
        help="root directory of onnxruntime-secure repository"
    )

    parser.add_argument(
        "--nnapi",
        action="store_true",
        help="Enable NNAPI support"
    )

    parser.add_argument(
        "--arch",
        nargs="+",                          # <-- require at least one
        choices=["arm64-v8a", "armeabi-v7a"],
        help="one or more architectures to build for"
    )

    parser.add_argument(
        "--no-neon",
        action="store_true",
        help="Disable NEON support for armeabi-v7a architecture"
    )

    parser.add_argument(
        "--build_shared_lib",
        action="store_true",
        help="Enable building shared library"
    )

    args = parser.parse_args()
    root = args.root.resolve().absolute()
    src_path = root / "_deps" / "onnxruntime-src"
    build_path = root / "_deps" / "onnxruntime-build" / "Android"
    install_path = root / "_deps" / "onnxruntime-install" / "Android"


    base_options = [
        '--android', 
        '--config', 'Release', 
        '--cmake_generator', 'Ninja',
        '--parallel',
        '--compile_no_warning_as_error',
        '--skip_submodule_sync',
        '--skip_tests',
        '--android_api', '22',
        '--android_sdk_path', str(root / '_deps' / 'android-sdk'),
        '--android_ndk_path', str(root / '_deps' / 'android-sdk' / 'ndk' / '27.2.12479018'),
    ]
    if args.build_shared_lib:
        base_options.append('--build_shared_lib')
    if args.nnapi:
        base_options.append('--use_nnapi')

    for arch in args.arch:
        print(f"Building ONNX Runtime for Android {arch}...")
        options = base_options + [
            '--android_abi', arch,
            '--build_dir', build_path / arch,
            '--target', 'install',
        ]
        cmake_options = {
            "CMAKE_INSTALL_PREFIX": install_path / arch,
            "CMAKE_C_FLAGS_RELEASE": "-O2 -g0",
            "CMAKE_CXX_FLAGS_RELEASE": "-O2 -g0",
            "CMAKE_SHARED_LINKER_FLAGS_RELEASE": "-s",
        }
        if args.no_neon:
            if arch == "armeabi-v7a":
                cmake_options['ANDROID_ARM_NEON'] = 'FALSE'
            else:
                print(f"Warning: --no-neon is only applicable to armeabi-v7a, ignoring for {arch}.")
        
        result = build(
            root, 
            options,
            cmake_options
            )
        if result.returncode != 0:
            print(f"Failed to build ONNX Runtime for {arch}.")
            sys.exit(result.returncode)
        else:
            print(f"ONNX Runtime for {arch} built and installed to {str(install_path / arch)}")
