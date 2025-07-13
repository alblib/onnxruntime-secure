import sys, platform, os, argparse, re
from pathlib import Path
import subprocess
from dataclasses import make_dataclass, fields

AndroidSDKPathClass = make_dataclass('AndroidSDKPathClass', [
    ('SDKPath', Path), ('NDKPath', Path),
    ('SDKAPIVersion', str), ('NDKVersion', str)
])

def get_android_sdk_paths(root):
    """
    Get the Android SDK and NDK paths from the root directory.
    :param root: The root directory of the onnxruntime-secure repository.
    :return: An instance of AndroidSDKPathClass with SDK and NDK paths.
    """

    # Check if the Android SDK path exists and get minimum API version
    ## SDKPath = sdk_path, SDKAPIVersion = min_api_version (like '22')
    sdk_path = root / '_deps' / 'android-sdk'
    if not sdk_path.exists():
        print("Android SDK path does not exist.")
        sys.exit(1)
    if not (sdk_path / 'platforms').exists():
        print("Android SDK platforms directory does not exist.")
        sys.exit(1)
    platform_regex = re.compile(r'android-(\d+)')
    platform_list = []
    for platform_name in os.listdir(str(sdk_path / 'platforms')):
        m = platform_regex.match(platform_name)
        if m:
            sdk_api_version = m.group(1)
            platform_list.append((sdk_api_version, platform_name))
    if not platform_list:
        print("No valid Android platforms found in SDK.")
        sys.exit(1)
    min_api_version, min_platform_name = min(platform_list, key=lambda x: x[0])
    
    # Check if the NDK path exists and get its version
    ## NDKPath = ndk_path, NDKVersion = ndk_version (like '27.2.12479018')
    ndk_parent_path = sdk_path / 'ndk'
    if not ndk_parent_path.exists():
        print("Android NDK path does not exist.")
        sys.exit(1)
    ndk_version = None
    try:
        ndk_version = max(
            (name for name in os.listdir(ndk_parent_path) if os.path.isdir(os.path.join(ndk_parent_path, name))),
            key=lambda x: list(map(int, x.split(".")))
        )
    except ValueError:
        print("No valid Android NDK version found.")
        sys.exit(1)
    ndk_path = ndk_parent_path / ndk_version

    return AndroidSDKPathClass(
        SDKPath=str(sdk_path.resolve().absolute()),
        NDKPath=str(ndk_path.resolve().absolute()),
        SDKAPIVersion=min_api_version, 
        NDKVersion=ndk_version
    )


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

    android_sdk_info = get_android_sdk_paths(root)

    base_options = [
        '--android', 
        '--config', 'Release', 
        '--cmake_generator', 'Ninja',
        '--parallel',
        '--compile_no_warning_as_error',
        '--skip_submodule_sync',
        '--skip_tests',
        '--android_api', android_sdk_info.SDKAPIVersion,
        '--android_sdk_path', android_sdk_info.SDKPath,
        '--android_ndk_path', android_sdk_info.NDKPath,
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
            "CMAKE_C_FLAGS_RELEASE": "-O2 -g0 -Wno-unused-parameter -Wno-unused-variable",
            "CMAKE_CXX_FLAGS_RELEASE": "-O2 -g0 -Wno-unused-parameter -Wno-unused-variable",
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
