#-----Zzz Setup python pip on Windows-----
# This script assumes that the repository is checked-out to this directory:
#   C:\Users\USERNAME\Documents\GitHub\vpntest\
# This script assumes that python is installed in this directory:
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Python310\python.exe
# user Path var:
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Python310
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Python310\Scripts
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Launcher\
# user PYTHONPATH var:
#   C:\Users\USERNAME\AppData\Local\zzzevpn\venv\Lib\site-packages
#   C:\Users\USERNAME\Documents\GitHub\vpntest\zzzapp\lib
#   C:\Users\USERNAME\Documents\GitHub\vpntest\zzzapp\lib\zzzevpn
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Python310\Lib
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Python310\DLLs
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Python310\Scripts
#   C:\Users\USERNAME\AppData\Local\Programs\Python\Python310\Tools
# Run this in a windows powershell:
#   cd "$($env:USERPROFILE)\Documents\GitHub\vpntest\windows"
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
#   Unblock-File -Path .\zzz_update_pip_windows.ps1
#   .\zzz_update_pip_windows.ps1

Write-Output "
#####################################################################
# Zzz Enhanced VPN - Setup/Update python dev environment on Windows #
#####################################################################

This script will setup/update the venv and python pypi packages.
"

# TODO: replace this with the more secure PowerShell username lookup?
#       [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$repos_name = "vpntest"
$repos_windows_subdir = "zzzevpn"
$venv_name = "venv-310"
$zzz_appdata_dir = "$($env:LOCALAPPDATA)\$repos_windows_subdir"
$zzz_venv_dir = "$zzz_appdata_dir\$venv_name"
$zzz_venv_scripts_dir = "$zzz_venv_dir\Scripts"
$zzz_venv_lib_dir = "$zzz_venv_dir\Lib"
$zzz_repos_dir = "$($env:USERPROFILE)\Documents\GitHub\$repos_name\install"
$python_dir = "$($env:LOCALAPPDATA)\Programs\Python\Python310"
$python_filepath = "$python_dir\python.exe"

# set the version to just "pip" to get the latest
$pip_version = "pip==24.2"
# $pip_version = "pip"

#--------------------------------------------------------------------------------

#-----verify basic tools are installed-----
# C:\Users\USERNAME\AppData\Local\Programs\Python\Python310\python.exe
if ( -Not (Test-Path "$python_dir")) {
    "ERROR: missing python directory $python_dir"
    exit
}

if ( -Not (Test-Path "$python_filepath")) {
    "ERROR: missing python executable $python_filepath"
    exit
}

if ( -Not (Test-Path "$zzz_appdata_dir")) {
    New-Item -Path "$($env:LOCALAPPDATA)" -Name "$repos_windows_subdir" -ItemType "directory"
    Write-Output "Created AppData directory:
    $zzz_appdata_dir
    "
}

if ( -Not (Test-Path "$zzz_venv_dir")) {
    New-Item -Path "$zzz_appdata_dir" -Name "$venv_name" -ItemType "directory"
    Write-Output "Created python venv directory:
    $zzz_venv_dir
    "
} else {
    Write-Output "Using existing python venv directory:
    $zzz_venv_dir
    "    
}


$should_proceed = ""
while (($should_proceed -ne "y") -and ($should_proceed -ne "n") -and ($should_proceed -ne "Y") -and ($should_proceed -ne "N")) {
    $should_proceed = Read-Host -Prompt "Proceed (y/n)?"
}
if (($should_proceed -eq "n") -or ($should_proceed -eq "N")) { exit }

#--------------------------------------------------------------------------------

#-----setup venv if it has not been setup yet-----
if (( -Not (Test-Path "$zzz_appdata_dir")) -or ( -Not (Test-Path "$zzz_venv_dir")) -or ( -Not (Test-Path "$zzz_venv_lib_dir"))) {
    #TODO: do the setup instead of throwing an error
    Write-Output "
    It looks like the venv has not been setup yet.
    Setting up venv...
    "

    #-----install python, pip, and virtualenv-----
    Write-Output "install pip:"
    & $python_dir\python -m ensurepip
    & $python_dir\python -m pip install --upgrade $pip_version
    Write-Output "install virtualenv:"
    & $python_dir\Scripts\pip install virtualenv

    #-----make the venv-----
    Write-Output "make the venv:"
    & $python_dir\Scripts\virtualenv $zzz_venv_dir
}

#--------------------------------------------------------------------------------

Write-Output "Updating Python PIP packages...
"

#-----Activate venv and upgrade pip-----
Write-Output "activate venv:"
& $zzz_venv_scripts_dir\activate.ps1
Write-Output "upgrade pip:"
& $zzz_venv_scripts_dir\python -m pip install --upgrade $pip_version

#-----install packages into the venv (run in this order)-----
Write-Output "install tools:"
& $zzz_venv_scripts_dir\pip install -r "$zzz_repos_dir\requirements-tools.txt"
Write-Output "install all pip files:"
& $zzz_venv_scripts_dir\pip install -r "$zzz_repos_dir\requirements.txt"

#-----deactivate the venv-----
deactivate
