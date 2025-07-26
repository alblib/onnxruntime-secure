import sys, platform, os, json
import subprocess
from typing import Union, Literal
from enum import Enum

class Target(Enum):
    Android = "Android"
    Windows = "Windows"
    macOS = "Darwin"
    iOS = "iOS"
    Linux = "Linux"

class Architecture(Enum):
    X64 = "AMD64"
    AARCH64 = "arm64-v8a"
    ARM32NEON = "armeabi-v7a"

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
            "CMAKE_INSTALL_PREFIX": install_path
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
                "CMAKE_C_FLAGS_RELEASE": "/Qspectre",
                "CMAKE_CXX_FLAGS_RELEASE": "/Qspectre",
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
        "--config", "Release",
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