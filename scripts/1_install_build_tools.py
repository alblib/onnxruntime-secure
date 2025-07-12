import os, sys, platform, subprocess, tempfile
from pathlib import Path
from urllib.request import urlretrieve
from dataclasses import make_dataclass, fields

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


def ensure_ninja():
    def check_ninja():
        try:
            result = subprocess.run(["ninja", "--version"], check=True)
            return result.returncode == 0
        except FileNotFoundError:
            print("Ninja build system is not installed. Please install it.")
            return False

    if not check_ninja():
        print("Installing Ninja build system...")
        system = platform.system()
        if system == 'Windows':
            result = subprocess.run([
                "winget", "install", "--exact",
                "--id", "Ninja-build.Ninja",
                ], check=True)
            if result.returncode != 0:
                print("Failed to install Ninja. Please install it manually from https://ninja-build.org/")
                sys.exit(1)
        elif system == 'Linux':
            result = subprocess.run([
                "sudo", "apt-get", "install", "-y",
                "ninja-build"
                ], check=True)
            if result.returncode != 0:
                print("Failed to install Ninja. Please install it manually from https://ninja-build.org/")
                sys.exit(1)
        elif system == 'Darwin':
            result = subprocess.run([
                "brew", "install", "ninja"
                ], check=True)
            if result.returncode != 0:
                print("Failed to install Ninja. Please install it manually from https://ninja-build.org/")
                sys.exit(1)
        else:
            print(f"Unsupported operating system: {system}")
            sys.exit(1)
        print("Ninja build system installed successfully.")
        # Return False to indicate that installation was performed and terminal needs to be restarted
        return False
    else:
        print("Ninja build system is already installed.")
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


def ensure_cmake():
    """
    Check if CMake is installed on the system, and if not, install it.
    """

    def is_cmake_installed():
        """
        Check if CMake is installed.
        """
        try:
            subprocess.run(["cmake", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    if not is_cmake_installed():
        system = platform.system()
        if system == 'Windows':
            print("CMake is not installed. Installing CMake using winget...")
            result = subprocess.run([
                "winget", "install", "--exact",
                "--id", "Kitware.CMake"
                ], check=True)
            if result.returncode != 0:
                print("Failed to install CMake. Please install it manually from https://cmake.org/download/")
                sys.exit(1)
        elif system == 'Linux':
            print("CMake is not installed. Installing CMake using apt-get...")
            result = subprocess.run(["sudo", "apt-get", "install", "-y", "cmake"], check=True)
            if result.returncode != 0:
                print("Failed to install CMake. Please install it manually from https://cmake.org/download/")
                sys.exit(1)
        elif system == 'Darwin':
            print("CMake is not installed. Installing CMake using Homebrew...")
            result = subprocess.run(["brew", "install", "--cask", "cmake-app"], check=True)
            if result.returncode != 0:
                print("Failed to install CMake. Please install it manually from https://cmake.org/download/")
                sys.exit(1)
        else:
            print(f"Unsupported operating system: {system}")
            sys.exit(1)
        print("CMake installed successfully.")
        # Return False to indicate that installation was performed and terminal needs to be restarted
        return False
    else:   
        print("CMake is already installed.")
        return True


def ensure_build_essential():
    """
    Check if build-essential is installed on Linux, and if not, install it.
    """

    def is_build_essential_installed():
        """
        Check if build-essential package is installed.
        """
        try:
            subprocess.run(["dpkg", "-l", "build-essential"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    if not is_build_essential_installed():
        print("build-essential is not installed. Installing build-essential...")
        result = subprocess.run(["sudo", "apt-get", "install", "-y", "build-essential"], check=True)
        if result.returncode != 0:
            print("Failed to install build-essential. Please install it manually.")
            sys.exit(1)
        print("build-essential installed successfully.")
        # Return False to indicate that installation was performed and terminal needs to be restarted
        return False
    else:
        print("build-essential is already installed.")
        return True


def ensure_java():
    """
    Check if Java is installed on the system, and if not, install it.
    """

    def is_java_installed():
        """
        Check if Java is installed.
        """
        try:
            subprocess.run(["java", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    if not is_java_installed():
        system = platform.system()
        if system == 'Windows':
            subprocess.run(["winget", "install", "--id", "EclipseAdoptium.Temurin.17.JDK", "-e"], check=True)
        elif system == 'Darwin':
            subprocess.run(["brew", "install", "--cask","temurin"], check=True)
        elif system == 'Linux':
            subprocess.run(["sudo", "apt", "install", "-y", "openjdk-17-jdk"], check=True)
        else:
            print(f"Unsupported operating system: {system}")
            sys.exit(1)
        print("JDK installed successfully.")
        return False
    else:
        print("JDK is already installed.")
        return True

def main():
    """Main function to ensure all build tools are installed.
    """
    result = True
    result &= ensure_cmake()
    result &= ensure_ninja()
    result &= ensure_java()

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

    if result:
        print("All build tools are installed and ready to use.")
    else:
        print("Some build tools were installed. Please restart your terminal to ensure they are available in the PATH.")
        sys.exit(1)


if __name__ == '__main__':
    main()
    