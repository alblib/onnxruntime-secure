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
        "--arch",
        nargs="+",                          # <-- require at least one
        choices=["x86", "x64", "arm64", "arm64ec", "arm32"],
        help="one or more architectures to build for"
    )

    args = parser.parse_args()
    root = args.root.resolve().absolute()
    src_path = root / "_deps" / "onnxruntime-src"
    build_path = root / "_deps" / "onnxruntime-build" / "Windows-DirectML"
    install_path = root / "_deps" / "onnxruntime-install" / "Windows-DirectML"

    system = platform.system()
    ver = platform.release()
    if system != 'Windows' or int(ver) < 10:
        print("Unsupported operating system for DirectML: Windows 10 or later is required.")
        sys.exit(1)

    if not os.path.isdir(src_path):
        print(f"ONNX Runtime source path does not exist: {src_path}")
        sys.exit(1)

    build_bat = src_path / "build.bat"
    if not os.path.isfile(build_bat):
        print(f"Build script not found: {build_bat}")
        sys.exit(1)

    base_options = [
        '--config', 'Release',
        '--cmake_generator', 'Visual Studio 17 2022',
        "--parallel",
        "--compile_no_warning_as_error",
        "--skip_submodule_sync",
        "--skip_tests",
        "--build_shared_lib",
    ]
    arch_options = {
        "x64": ['--use_dml'],
        "x86": ['--x86', '--use_dml'],
        "arm32": ['--arm'],
        "arm64": ['--arm64', '--use_dml'],
        "arm64ec": ['--arm64ec', '--use_dml'],
    }
    base_cmake_extra_defines = [
        'CMAKE_C_FLAGS=/Qspectre',
        'CMAKE_CXX_FLAGS=/Qspectre',
    ]
    build_dir = {
        "x64": build_path / "x64",
        "arm64": build_path / "ARM64",
    }
    install_dir = {
        "x64": install_path / "x64",
        "arm64": install_path / "ARM64",
    }

    for arch in arch_options.keys():
        build_dest = str(build_path / arch)
        install_dest = str(install_path / arch)
        try:
            install_dest = os.path.relpath(
                install_dest, build_dest)
        except ValueError:
            pass
        args = base_options + arch_options[arch] + [
            '--build_dir', build_dest,
            '--target', 'install',
            '--cmake_extra_defines', *base_cmake_extra_defines, 
            f'CMAKE_INSTALL_PREFIX={install_dest}',
        ]
        print(f"Building ONNX Runtime for {arch}...")
        result = subprocess.run([str(build_bat)] + args, check=True)
        if result.returncode != 0:
            print(f"Failed to build ONNX Runtime for {arch}.")
            sys.exit(result.returncode)
        else:
            print(f"ONNX Runtime for {arch} built and installed to {str(install_dir[arch])}")
