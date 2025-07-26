import sys, platform, os, json, argparse
import subprocess
from typing import Union
from enum import Enum
from pathlib import Path

class Target(Enum):
    Android = "Android"
    Windows = "Windows"
    macOS = "Darwin"
    iOS = "iOS"
    Linux = "Linux"

class Architecture(Enum):
    X64 = "x64"
    AARCH64 = "arm64-v8a"
    ARM32NEON = "armeabi-v7a"

available_archs = {
    Target.Android: [Architecture.AARCH64, Architecture.ARM32NEON],
    Target.Windows: [Architecture.X64, Architecture.AARCH64],
    Target.macOS: [Architecture.AARCH64, Architecture.X64],
    Target.iOS: [Architecture.AARCH64],
    Target.Linux: [Architecture.X64, Architecture.AARCH64, Architecture.ARM32NEON]
}

class AndroidEnvironment:
    def __init__(
            self, 
            SDKAPIVersion: Union[None, str, int] = None, 
            NDKVersion: Union[None, str] = None
            ):
        if SDKAPIVersion is None or NDKVersion is None:
            with open(os.path.join(os.path.dirname(__file__), 'sdk_version.json'), 'r') as sources_src:
                android_versions = json.load(sources_src)['android']
                if NDKVersion is None:
                    NDKVersion = android_versions['ndk']
                if SDKAPIVersion is None:
                    SDKAPIVersion = android_versions['platform']

        system = platform.system()
        arch = platform.machine()
        if system == 'Darwin':
            self.SDKPath = '/opt/homebrew/share/android-commandlinetools'
        elif system == 'Linux' and arch == 'x86_64':
            self.SDKPath = '/opt/android-sdk'
        elif system == 'Windows' and arch == 'AMD64':
            self.SDKPath = os.path.join(os.environ.get("USERPROFILE"), 'AndroidSDK')
        else:
            print(f"Unsupported operating system: {system}:{arch}")
            sys.exit(1)
        try:
            self.SDKAPIVersion = int(str(SDKAPIVersion))
        except:
            if isinstance(SDKAPIVersion, str) and SDKAPIVersion.startswith('android-'):
                try:
                    self.SDKAPIVersion = int(SDKAPIVersion[8:])
                except:
                    raise Exception('incorrect SDKAPIVersion')
            else:
                raise Exception('incorrect SDKAPIVersion')
        self.NDKVersion = NDKVersion
        self.NDKPath = os.path.join(self.SDKPath, 'ndk', self.NDKVersion)

    def cmake_options(self):
        return {
            "ANDROID_SDK": self.SDKPath,
            "CMAKE_TOOLCHAIN_FILE": os.path.join(self.NDKPath, 'build', 'cmake', 'android.toolchain.cmake'),
            "ANDROID_PLATFORM": self.SDKAPIVersion,
            "ANDROID_MIN_SDK_VERSION": self.SDKAPIVersion,
        }

def build(
        source_path, 
        build_path, 
        install_path, 
        target: Target,
        arch: Architecture,
        cmake_options: dict = {}, 
        ):
    source_path = str(os.path.abspath(source_path))
    build_path = str(os.path.abspath(build_path))
    install_path = str(os.path.abspath(install_path))
    cmake_options.update(
        {
            "CMAKE_INSTALL_PREFIX": install_path,
            "CMAKE_BUILD_TYPE": "Release",
            "CMAKE_WARN_DEPRECATED": "OFF",
        }
    )

    cmake_generator = ""
    cmake_architecture = ""
    if target == Target.Android:
        cmake_generator = "Ninja"
        if arch == Architecture.ARM32NEON:
            abi = 'armeabi-v7a'
        elif arch == Architecture.AARCH64:
            abi = 'arm64-v8a'
        else:
            print("Unsupported architecture. Use ARM-* for android.")
            sys.exit(1)
        cmake_options.update({"ANDROID_ABI": abi})
        cmake_options.update(AndroidEnvironment().cmake_options())
        cmake_options.update( # remove forced '-g' debug flag in android toolchain
            {
                "CMAKE_C_FLAGS_RELEASE": "-O2 -g0 -Wno-unused-parameter -Wno-unused-variable",# -mspeculative-load-hardening -mindirect-branch=thunk -mindirect-branch-register -mfunction-return=thunk",
                "CMAKE_CXX_FLAGS_RELEASE": "-O2 -g0 -Wno-unused-parameter -Wno-unused-variable",# -mspeculative-load-hardening -mindirect-branch=thunk -mindirect-branch-register -mfunction-return=thunk",
                "CMAKE_SHARED_LINKER_FLAGS_RELEASE": "-s",
            }
        )
        # Disable Optionals
        cmake_options.update(
            {
                "BUILD_ANDROID_EXAMPLES": "OFF",
                "BUILD_ANDROID_PROJECTS": "OFF",
                "BUILD_KOTLIN_EXTENSIONS": "OFF",
                "WITH_VULKAN": "ON",
            }
        )
    elif target == Target.Windows:
        cmake_generator = 'Visual Studio 17 2022'
        if arch == Architecture.X64:
            cmake_architecture = 'AMD64'
        elif arch == Architecture.AARCH64:
            cmake_architecture = 'ARM64'
        else:
            print("Unsupported architecture. Use AMD64 or ARM64 for MSVC.")
            sys.exit(1)
        cmake_options.update( # Use Spectre-mitigated libs for security
            {
                # Use Spectre-mitigated libs for security
                "CMAKE_C_FLAGS_RELEASE": "/Qspectre",
                "CMAKE_CXX_FLAGS_RELEASE": "/Qspectre",
                # Enable OpenCL
                "WITH_OPENCL": "ON",
            }
        )

    elif target == Target.macOS or target == Target.iOS:
        cmake_generator = 'Xcode'

    # Disable Optionals
    cmake_options.update(
        {
            "BUILD_FAT_JAVA_LIB": "OFF",
            "BUILD_JAVA": "OFF",
            "BUILD_PERF_TESTS": "OFF",
            "BUILD_TESTS": "OFF",
        }
    )

    subprocess_args = [
        "cmake", 
        "-S", source_path,
        "-B", build_path,
    ]
    if cmake_generator:
        subprocess_args += ['-G', cmake_generator]
    if cmake_architecture:
        subprocess_args += ['-A', cmake_architecture]
    for tag, val in cmake_options.items():
        subprocess_args.append(f'-D{tag}={val}')
    result = subprocess.run(
        subprocess_args,
        check=True
    )
    if result.returncode != 0:
        print(f"Failed to build OpenCV.")
        sys.exit(result.returncode)
    result = subprocess.run(
        [
            'cmake', '--build', build_path,
            '--target', 'install',
            '--config', 'Release',
            '--parallel',
            f'-j{os.cpu_count()}', 
        ], check=True
    )
    if result.returncode != 0:
        print(f"Failed to build OpenCV.")
        sys.exit(result.returncode)


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
        "--build_shared_lib",
        help="enable shared library build",
        action="store_true"
    )

    parser.add_argument(
        "--arch",
        nargs="+",                          # <-- require at least one
        choices=[a.value for a in Architecture],
        help="one or more architectures to build for"
    )

    parser.add_argument(
        "--platform",
        nargs="+",                          # <-- require at least one
        choices=[t.value for t in Target],
        help="one or more architectures to build for"
    )

    # Parse arguments; will auto-exit and print usage on error
    args = parser.parse_args()
    root = args.root.resolve()

    deps_path = os.path.abspath(os.path.join(root, '_deps'))
    src_path = os.path.join(deps_path, 'opencv-src')
    build_root = os.path.join(deps_path, 'opencv-build')
    install_root = os.path.join(deps_path, 'opencv-install')

    target_platforms = [Target(t) for t in args.platform]
    target_archs = [Architecture(a) for a in args.arch]
    for target_platform in target_platforms:
        build_path = os.path.join(build_root, target_platform.value)
        install_path = os.path.join(install_root, target_platform.value)

        for arch in available_archs[target_platform]:
            if arch not in target_archs:
                continue
                
            build_path = os.path.join(build_path, arch.value, 'shared' if args.build_shared_lib else 'static')
            install_path = os.path.join(install_path, arch.value, 'shared' if args.build_shared_lib else 'static')
            build(src_path, build_path, install_path, Target(target_platform), Architecture(arch),
                  {"BUILD_SHARED_LIBS": "ON" if args.build_shared_lib else "OFF"}
                  )