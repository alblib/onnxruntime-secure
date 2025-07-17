import os, sys, platform, subprocess, tempfile, argparse, fnmatch
from pathlib import Path
from urllib.request import urlretrieve
from dataclasses import make_dataclass, fields
import zipfile


def ensure_msvc2022():
    VSInstallerUtilities = make_dataclass('VSInstallerUtilities', [
        ('vswhere', str), ('setup', str)
    ])
    VS2022InstallInfo = make_dataclass('VS2022InstallInfo', [
        ('channelId', str), ('productId', str), ('installationPath', str),
        ])
    VSComponent = make_dataclass('VSComponent', [
        ('name', str), ('id', str), ('version', str)
    ])

    vs_required_components = [
        VSComponent(
            name='MSVC v143 - VS 2022 C++ x64/x86 build tools (Latest)', 
            id='Microsoft.VisualStudio.Component.VC.Tools.x86.x64', 
            version=''),
        VSComponent(
            name='MSVC v143 - VS 2022 C++ ARM64/ARM64EC build tools (Latest)', 
            id='Microsoft.VisualStudio.Component.VC.Tools.ARM64', 
            version=''),
        VSComponent(
            name='MSVC v143 - VS 2022 C++ ARM build tools (Latest)', 
            id='Microsoft.VisualStudio.Component.VC.Tools.ARM', 
            version=''),
        VSComponent(
            name='MSVC v143 - VS 2022 C++ x64/x86 Spectre-mitigated libs (Latest)', 
            id='Microsoft.VisualStudio.Component.VC.Runtimes.x86.x64.Spectre', 
            version=''),
        VSComponent(
            name='MSVC v143 - VS 2022 C++ ARM64/ARM64EC Spectre-mitigated libs (Latest)', 
            id='Microsoft.VisualStudio.Component.VC.Runtimes.ARM64.Spectre', 
            version=''),
        VSComponent(
            name='MSVC v143 - VS 2022 C++ ARM Spectre-mitigated libs (Latest)', 
            id='Microsoft.VisualStudio.Component.VC.Runtimes.ARM.Spectre',
            version=''),
        VSComponent(
            name='C++ CMake tools for Windows', 
            id='Microsoft.VisualStudio.Component.VC.CMake.Project',
            version=''),
    ]
    
    # Get Installer Executables
    pf86 = os.environ.get("ProgramFiles(x86)")
    vs_installer_utilities_tuple_list = \
        [
            (
                util.name,
                os.path.join(
                    pf86, 
                    "Microsoft Visual Studio",
                    "Installer",
                    f"{util.name}.exe"
                ) if util.name else ""
            )
            for util in fields(VSInstallerUtilities)
        ]
    vs_installer_utilities = VSInstallerUtilities(**dict(vs_installer_utilities_tuple_list))
    ## If no VS installer utilities are found, vs_installer_utilities.vswhere = ""

    # Get VS2022 Installation Info
    install_info_tuple_list = []
    if vs_installer_utilities.vswhere:
        for installPropertyId in fields(VS2022InstallInfo):
            result = subprocess.run(
                [
                    vs_installer_utilities.vswhere,
                    "-latest",
                    "-products", "*",
                    "-version", "[17.0,18.0)", # VS2022(17)
                    "-property", installPropertyId.name
                ],
                capture_output=True, text=True
            )
            property = result.stdout.strip() if result.returncode == 0 else ""
            install_info_tuple_list.append((installPropertyId.name, property))
    else:
        install_info_tuple_list = [(propId.name, "") for propId in fields(VS2022InstallInfo)]
    install_info = VS2022InstallInfo(**dict(install_info_tuple_list))
    ## If no VS2022 are found, install_info.installationPath = ""

    # Get Component Installation Info
    if vs_installer_utilities.vswhere:
        for i in range(len(vs_required_components)):
            result = subprocess.run(
                [
                    vs_installer_utilities.vswhere,
                    "-latest",
                    "-products", "*",
                    "-requires", vs_required_components[i].id,
                    "-property", "installationVersion"
                ],
                capture_output=True, text=True
            )
            vs_required_components[i].version = result.stdout.strip() if result.returncode == 0 else ""

    # Print and Action
    if not vs_installer_utilities.setup:
        # 1. Ensure Downloads folder exists
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        # 2. Create a temp file in Downloads with .exe suffix
        tmp_file = tempfile.NamedTemporaryFile(
            dir=downloads_dir, suffix=".exe", delete=False
        )
        tmp_path = Path(tmp_file.name)
        tmp_file.close()  # close so urlretrieve can write to it
        # 3. Download the VS Community installer
        url = "https://aka.ms/vs/17/release/vs_community.exe"
        urlretrieve(url, str(tmp_path))
        # 4. Specify the installer as the setup utility
        vs_installer_utilities.setup = str(tmp_path)
        vs_installer_utilities.vswhere = ""

    not_installed_comps = [comp for comp in vs_required_components if not comp.version]
    if not_installed_comps:
        print(f'ERROR: These components are not installed and required to be installed: {[comp.name for comp in not_installed_comps]}')
        not_installed_comps_ids = [comp.id for comp in not_installed_comps]
        subprocess.run(
            [
                vs_installer_utilities.setup,
                "modify",
            ] + [token for item in not_installed_comps_ids for token in ('--add', item)]
            +[
                '--channelId', install_info.channelId,
                '--productId', install_info.productId,
            ],
        )
        sys.exit(1)

    else:
        print("All required components are installed.")
        print(f"Visual Studio 2022 installation path: {install_info.installationPath}")
        print(f"Visual Studio Installer Utilities: {vs_installer_utilities.vswhere}, {vs_installer_utilities.setup}")
        return True


def ensure_xcode():
    """
    Check if Xcode is installed on macOS, and if not, prompt the user to install it.
    """

    def is_xcode_installed():
        """
        Check if Xcode command line tools are installed.
        """
        try:
            subprocess.run(["xcode-select", "--install"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
        

    if not is_xcode_installed():
        print("Xcode is not installed. Please install it from the App Store.")
        sys.exit(1)

    print("Xcode command line tools are already installed.")
    return True


def ensure_apt_packages(name, packages):
    """
    Check if build-essential is installed on Linux, and if not, install it.
    """

    def is_package_installed(package):
        """
        Check if build-essential package is installed.
        """
        try:
            subprocess.run(["dpkg", "-l", package], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
        
    to_install = []
    for package in packages:
        if not is_package_installed(package):
            to_install.append(package)

    if to_install:
        print(f"{name} is not fully installed. Installing ...")
        result = subprocess.run(["sudo", "apt-get", "install", "-y"] + to_install, check=True)
        if result.returncode != 0:
            print(f"Failed to install {to_install}. Please install it manually.")
            sys.exit(1)
        print(f"{name} installed successfully.")
        # Return False to indicate that installation was performed and terminal needs to be restarted
        return False
    else:
        print(f"{name} is already installed.")
        return True

def ensure_build_essential():
    """
    Check if build-essential is installed on Linux, and if not, install it.
    """
    return ensure_apt_packages('build-essential', ['build-essential'])


Package = make_dataclass('Package', [
    ('name', str),
    ('command', str), 
    ('winget_package_name', str),
    ('brew_package_name', str),
    ('apt_package_name', str),
    ('is_brew_cask', bool),
    ('url', str)
])

def ensure_package(package):
    def check_package():
        try:
            result = subprocess.run([package.command, "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except FileNotFoundError:
            print(f"{package.name} is not installed. Please install it.")
            return False

    fail_message = f'Failed to install {package.name}.'
    if package.url:
        fail_message += f' Please install it manually from {package.url}'
    else:
        fail_message += ' Please install it manually.'

    if not check_package():
        system = platform.system()
        if system == 'Windows':
            if not package.winget_package_name:
                return False
            print(f"Installing {package.name} ...")
            result = subprocess.run([
                "winget", "install", "--exact",
                "--id", package.winget_package_name,
                ], check=True)
            if result.returncode != 0:
                print(fail_message)
                sys.exit(1)
        elif system == 'Linux':
            if not package.apt_package_name:
                return False
            print(f"Installing {package.name} ...")
            result = subprocess.run([
                "sudo", "apt-get", "install", "-y",
                package.apt_package_name
                ], check=True)
            if result.returncode != 0:
                print(fail_message)
                sys.exit(1)
        elif system == 'Darwin':
            if not package.brew_package_name:
                return False
            print(f"Installing {package.name} ...")
            runner = ['brew', 'install']
            if package.is_brew_cask:
                runner.append('--cask')
            runner.append(package.brew_package_name)
            result = subprocess.run(runner, check=True)
            if result.returncode != 0:
                print(fail_message)
                sys.exit(1)
        else:
            print(f"Unsupported operating system: {system}")
            sys.exit(1)
        print(f"{package.name} installed successfully.")
        # Return False to indicate that installation was performed and terminal needs to be restarted
        return False
    else:
        print(f"{package.name} is already installed.")
        return True

def ensure_ninja():
    return ensure_package(
        Package(
            name='Ninja',
            command='ninja',
            winget_package_name='Ninja-build.Ninja',
            apt_package_name='ninja-build',
            brew_package_name='ninja',
            is_brew_cask=False,
            url='https://ninja-build.org/'
        )
    )
    
def ensure_cmake():
    return ensure_package(
        Package(
            name='CMake',
            command='cmake',
            winget_package_name='Kitware.CMake',
            apt_package_name='cmake',
            brew_package_name='cmake-app',
            is_brew_cask=True,
            url='https://cmake.org/download/'
        )
    )


def ensure_java():
    return ensure_package(
        Package(
            name='Java JDK',
            command='java',
            winget_package_name='EclipseAdoptium.Temurin.17.JDK',
            apt_package_name='openjdk-17-jdk',
            brew_package_name='temurin',
            is_brew_cask=True,
            url='https://www.java.com/'
        )
    )


def ensure_android_sdkmanager():
    if not ensure_java():
        return False

    if not ensure_package(
        Package(
            name='Android SDK',
            command='sdkmanager',
            winget_package_name='',
            apt_package_name='sdkmanager',
            brew_package_name='android-commandlinetools',
            is_brew_cask=True,
            url='https://developer.android.com/studio'
        )
    ):
        uf = os.environ.get("USERPROFILE")
        AndroidFolder = os.path.join(uf, 'AndroidSDK')
        if not os.path.exists(os.path.join(AndroidFolder, 'cmdline-tools/sdkmanager.bat')):
            print('Installing Android SDK Manager...')
            if not os.path.exists(AndroidFolder):
                os.makedirs(AndroidFolder)
            url = f"https://dl.google.com/android/repository/commandlinetools-win-13114758_latest.zip"
            try:
                urlretrieve(url, os.path.join(AndroidFolder, 'android-cmdline-tools.zip'))
            except:
                return False
            try:
                with zipfile.ZipFile(os.path.join(AndroidFolder, 'android-cmdline-tools.zip'), 'r') as zip_ref:
                    zip_ref.extractall(AndroidFolder)
            except:
                if os.path.exists(os.path.join(AndroidFolder, 'android-cmdline-tools.zip')):
                    os.remove(os.path.join(AndroidFolder, 'android-cmdline-tools.zip'))
                return False
            os.remove(os.path.join(AndroidFolder, 'android-cmdline-tools.zip'))
            print('Android SDK Manager installed successfully.')
        else:
            print('Android SDK Manager is already installed.')
        sdkmanager = os.path.join(AndroidFolder, 'cmdline-tools/bin/sdkmanager.bat')
        result = subprocess.run([
            sdkmanager, 
            "--install", 
            "platform-tools", 
            "platforms;android-22", 
            "build-tools;22.0.1", 
            "ndk;27.2.12479018",
            f"--sdk_root={AndroidFolder}",
            ], check=True)
    else:
        sdkmanager = 'sdkmanager'
        result = subprocess.run([
            'sdkmanager', 
            "--install", 
            "platform-tools", 
            "platforms;android-22", 
            "build-tools;22.0.1", 
            "ndk;27.2.12479018",
            ], check=True)
        
    return result.returncode == 0


def main():
    """
    Main function to ensure all build tools are installed.
    """

    parser = argparse.ArgumentParser(
        prog="1_install_build_tools",
        description="Install build tools"
    )

    parser.add_argument(
        "--install-android-sdk",
        action="store_true",
        help="Install Android SDK"
    )

    args = parser.parse_args()

    result = True
    result &= ensure_cmake()
    result &= ensure_ninja()

    system = platform.system()
    if system == 'Windows':
        result &= ensure_msvc2022()
    elif system == 'Linux':
        result &= ensure_build_essential()
    elif system == 'Darwin':
        result &= ensure_xcode()
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

    if args.install_android_sdk:
        result &= ensure_android_sdkmanager()

    if result:
        print("All build tools are installed and ready to use.")
    else:
        print("Some build tools were installed. Please restart your terminal to ensure they are available in the PATH.")
        sys.exit(1)


if __name__ == '__main__':
    main()
    