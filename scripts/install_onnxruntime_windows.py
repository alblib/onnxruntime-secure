import os, subprocess, shutil, shlex, tempfile
from pathlib import Path
from urllib.request import urlretrieve
from dataclasses import make_dataclass, fields

deps_dir = os.path.join(os.path.dirname(__file__), '../_deps')
os.makedirs(deps_dir, exist_ok=True)

# Update onnxruntime src
def update_onnxruntime_src():  # -> int
    ort_src_dir = os.path.join(deps_dir, 'onnxruntime-src')
    if os.path.isdir(ort_src_dir):
        if os.path.isdir(os.path.join(ort_src_dir, '.git')):
            if subprocess.run(
                ['git', 'reset', '--hard', 'origin/main'],
                cwd=ort_src_dir
            ).returncode == 0:
                return
        shutil.rmtree(ort_src_dir)
    return subprocess.run(
        ['git', 'clone', 'https://github.com/microsoft/onnxruntime.git', 'onnxruntime-src'],
        cwd=deps_dir
    ).returncode


def check_vs2022():

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
    ]
    
    # Get Installer Executables
    pf86 = os.environ.get("ProgramFiles(x86)")
    vs_installer_utilities_tuple_list = \
        [
            (
                utilname,
                os.path.join(
                    pf86, 
                    "Microsoft Visual Studio",
                    "Installer",
                    f"{utilname}.exe"
                ) if utilname else ""
            )
            for utilname in fields(VSInstallerUtilities)
        ]
    vs_installer_utilities = VSInstallerUtilities(**dict(vs_installer_utilities_tuple_list))

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
                    "-property", installPropertyId
                ],
                capture_output=True, text=True
            )
            property = result.stdout.strip() if result.returncode != 0 else ""
            install_info_tuple_list.append((installPropertyId, property))
    else:
        install_info_tuple_list = [(propId, "") for propId in fields(VS2022InstallInfo)]
    install_info = VS2022InstallInfo(**dict(install_info_tuple_list))

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
            vs_required_components[i].version = result.stdout.strip() if result.returncode != 0 else ""

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
        # 4. Execute the installer
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

    if not vs_installer_utilities.vswhere:
        # 5. Remove the temp file when done
        tmp_path.unlink()




    # for name, id in vs_required_components:
    #     spectre_args = [
    #         vswhere,
    #         "-latest",
    #         "-products", "*",
    #         "-requires", id,
    #         "-property", "installationVersion"
    #     ]
    #     res2 = subprocess.run(spectre_args, capture_output=True, text=True)
    #     res2_ver = res2.stdout.strip()
    #     if res2_ver:
    #         print(f'Component "{name}" is installed with version {res2_ver}.')
    #     else:
    #         print(f'ERROR: Component "{name}" is NOT installed')
    #         not_installed_names.append(name)

    # if not_installed_names:
    #     print(f'INSTALL VS2022 Components {not_installed_names}')


    #     # (Optional) capture_output/text for programmatic use
    #     result = subprocess.run(args, capture_output=True, text=True)

    #     # 4) Check results
    #     if result.returncode != 0:
    #         # print("vswhere failed:", result.stderr)
    #         return None
    #     else:
    #         print("Visual Studio 2022 is installed in ", result.stdout.strip())
    #         return vswhere


    # def vswhere_vs2022():

    #     # 1) Read the 32-bit Program Files path
    #     pf86 = os.environ.get("ProgramFiles(x86)")
    #     if not pf86:
    #         raise RuntimeError("Environment variable ProgramFiles(x86) not found")

    #     # 2) Build the vswhere.exe path
    #     vs_installer_utilities_tuple_list = \
    #         [
    #             (
    #                 utilname,
    #                 os.path.join(
    #                     pf86, 
    #                     "Microsoft Visual Studio",
    #                     "Installer",
    #                     f"{utilname}.exe"
    #                 ) if utilname else ""
    #             )
    #             for utilname in fields(VSInstallerUtilities)
    #         ]
    #     vs_installer_utilities = VSInstallerUtilities(**dict(vs_installer_utilities_tuple_list))

    #     vswhere = os.path.join(
    #         pf86,
    #         "Microsoft Visual Studio",
    #         "Installer",
    #         "vswhere.exe"
    #     )
    #     setup = os.path.join(
    #         pf86,
    #         "Microsoft Visual Studio",
    #         "Installer",
    #         "vswhere.exe"
    #     )

    #     if not os.path.isfile(vswhere):
    #         # raise FileNotFoundError(f"vswhere.exe not found at {vswhere!r}")
    #         return None

    #     # 3) Invoke vswhere with whatever args you need
    #     args = [
    #         vswhere,
    #         "-latest",
    #         "-products", "*",
    #         "-version", "[17.0,18.0)", # VS2022(17)
    #         "-property", "installationPath"
    #     ]


    #     # (Optional) capture_output/text for programmatic use
    #     result = subprocess.run(args, capture_output=True, text=True)

    #     # 4) Check results
    #     if result.returncode != 0:
    #         # print("vswhere failed:", result.stderr)
    #         return None
    #     else:
    #         print("Visual Studio 2022 is installed in ", result.stdout.strip())
    #         return vswhere

    # vswhere = vswhere_vs2022()
    # if not vswhere:
    #     print('ERROR: Visual Studio 2022 is not present. ' \
    #         'Installing Visual Studio 2022... ' \
    #         f'Please install with individual components {[name for name, _ in vs_required_components]}')
    #     return 1

    # not_installed_names = []
    # for name, id in vs_required_components:
    #     spectre_args = [
    #         vswhere,
    #         "-latest",
    #         "-products", "*",
    #         "-requires", id,
    #         "-property", "installationVersion"
    #     ]
    #     res2 = subprocess.run(spectre_args, capture_output=True, text=True)
    #     res2_ver = res2.stdout.strip()
    #     if res2_ver:
    #         print(f'Component "{name}" is installed with version {res2_ver}.')
    #     else:
    #         print(f'ERROR: Component "{name}" is NOT installed')
    #         not_installed_names.append(name)

    # if not_installed_names:
    #     print(f'INSTALL VS2022 Components {not_installed_names}')

def build_onnxruntime_windows():
    if check_vs2022():
        return 1
    if update_onnxruntime_src():
        return 1
    
    arch_flags = [
        ('x64', ['--use_dml',]),
        ('ARM64', ['--arm64', '--use_dml',]),
        ('x86', ['--x86', '--use_dml',]),
        ('ARM', ['--arm',]),
    ]
    for arch, flags in arch_flags:
        print(f'Building for Windows {arch}...')
        if subprocess.run(
            [
                '\.build.bat',
                '--cmake_generator="Visual Studio 17 2022"',
                '--config', 'Release', '--parallel',
                '--target', 'install',
            ] + flags + [
                '--build_dir', f'../onnxruntime-build/Windows/{arch}',
                '--compile_no_warning_as_error',
                '--skip_tests',
                '--build_shared_lib',
            ] + [
                '--cmake_extra_defines', 
                'CMAKE_C_FLAGS="/Qspectre"', 
                'CMAKE_CXX_FLAGS="/Qspectre"', 
                'CMAKE_INSTALL_PREFIX="../../../onnxruntime-install/Windows/x64"',
            ],
            cwd=os.path.join(deps_dir, 'onnxruntime-src')
        ).returncode:
            print(f'ERROR: Build for Windows {arch} Failed.')
            return 1
        else:
            print(f'Building for Windows {arch}...Success.')


# check_vs2022()