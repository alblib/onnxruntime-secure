import sys, platform, os, argparse
from pathlib import Path
from enum import Enum
import subprocess


if __name__ == "__main__":
    """
    Ensure the DirectML repository is cloned and updated.
    """

    parser = argparse.ArgumentParser(
        prog="3_install_onnxruntime_windows",
        description="Build and install onnxruntime for Windows"
    )
    parser.add_argument(
        "root",
        type=Path,
        metavar="root",
        help="root directory of onnxruntime-secure repository"
    )
    parser.add_argument(
        "--ios",
        help="enable iOS support",
        action="store_true"
    )
    parser.add_argument(
        "--use_coreml",
        help="enable CoreML support",
        action="store_true"
    )
    parser.add_argument(
        "--build_shared_lib",
        help="enable shared library build",
        action="store_true"
    )

    args = parser.parse_args()
    root = args.root.resolve().absolute()
    src_path = root / "_deps" / "onnxruntime-src"
    if args.ios:
        build_path = root / "_deps" / "onnxruntime-build" / "iOS"
        install_path = root / "_deps" / "onnxruntime-install" / "iOS"
    else:
        build_path = root / "_deps" / "onnxruntime-build" / "macOS"
        install_path = root / "_deps" / "onnxruntime-install" / "macOS"

    system = platform.system()
    if system != 'Darwin':
        print("Unsupported operating system for DirectML: macOS is required.")
        sys.exit(1)

    if not os.path.isdir(src_path):
        print(f"ONNX Runtime source path does not exist: {src_path}")
        sys.exit(1)

    build_bat = src_path / "build.sh"
    if not os.path.isfile(build_bat):
        print(f"Build script not found: {build_bat}")
        sys.exit(1)

    base_options = [
        '--config', 'Release',
        '--use_xcode',
        "--parallel",
        "--compile_no_warning_as_error",
        "--skip_submodule_sync",
        "--skip_tests",
    ]
    cmake_extra_defines = []
    if args.build_shared_lib:
        base_options.append('--build_shared_lib')
    if args.ios:
        base_options += [
            '--ios', 
            '--apple_sysroot', 'iphoneos', 
            '--osx_arch', 'arm64', 
            '--apple_deploy_target', '15.0'
            ]
    else:
        base_options += [
            '--apple_deploy_target', '11.0'
            ]
        cmake_extra_defines += [
            'CMAKE_OSX_ARCHITECTURES="arm64;x86_64"'
        ]
    if args.use_coreml:
        base_options.append('--use_coreml')
    base_options += ['--build_dir', str(build_path)]
    cmake_extra_defines += [
        'CMAKE_INSTALL_PREFIX=' + str(install_path)
    ]
    options = base_options + ['--cmake_extra_defines', *cmake_extra_defines]

    build_dest = str(build_path.resolve().absolute())
    install_dest = str(install_path.resolve().absolute())
    try:
        install_dest = os.path.relpath(
            install_dest, build_dest)
    except ValueError:
        pass

    print(f"Building ONNX Runtime for {'iOS' if args.ios else 'macOS'}...")
    result = subprocess.run([str(build_bat)] + options, check=True)
    if result.returncode != 0:
        print(f"Failed to build ONNX Runtime for {'iOS' if args.ios else 'macOS'}.")
        sys.exit(result.returncode)
    else:
        print(f"ONNX Runtime for {'iOS' if args.ios else 'macOS'} built and installed to {str(install_path.resolve().absolute())}")
