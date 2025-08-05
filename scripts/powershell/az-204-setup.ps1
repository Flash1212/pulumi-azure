# PowerShell script to set up the environment for AZ-204 exam preparation
# This script installs IIS, Chocolatey, and some common development tools.

function setup_iis {

    Write-Host "Setting up IIS..."
    $az204_app_name = 'az-204-dotnet-app'
    # Create the application directory
    $az204_app_path = "C:\$az204_app_name"
    New-Item -Path $az204_app_path -ItemType Directory -Force
    Install-WindowsFeature -name Web-Server -IncludeManagementTools
    # Give IIS time to startup
    Start-Sleep -Seconds 10
    Import-Module WebAdministration
    Set-WebBinding -Name 'Default Web Site' -BindingInformation '*:80:' -PropertyName Port -Value 8080
    # Create a new site for the application
    New-Website -Name 'AZ204' -Port 80 -PhysicalPath "$az204_app_path" -Force
    Write-Host "IIS has been enabled."
}

function install_chocolatey {
    Write-Host "Installing Chocolatey..."
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    choco feature disable --name=showDownloadProgress
    Write-Host "Chocolatey has been installed."
}

function install_choco_apps {
    Write-Host "Installing Chocolatey applications..."
    choco install git vscode dotnet-8.0-windowshosting python3 -y --force --allow-empty-checksums
    Write-Host "Chocolatey applications have been installed."
}

function main {
    Write-Host "Starting AZ-204 setup..."
    setup_iis
    install_chocolatey
    install_choco_apps
    Write-Host "AZ-204 setup completed."
}

$setup_output = "C:\az204-setup-output.txt"
main *>&1 | Out-File -FilePath $setup_output
