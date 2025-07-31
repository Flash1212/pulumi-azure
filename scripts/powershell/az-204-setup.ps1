
function install-chocolatey {
    Write-Host "Installing Chocolatey..."
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "Chocolatey has been installed."
}

function install-dotnet-hosting {
    Write-Host "Installing ASP.NET..."
    choco install dotnet-8.0-windowshosting -y
    Write-Host "ASP.NET has been installed."
}

function install-python3 {
    Write-Host "Installing Python 3..."
    choco install python3 -y
    Write-Host "Python 3 has been installed."
}

function enable-iss {
    Write-Host "Enabling IIS..."
    Install-WindowsFeature -name Web-Server -IncludeManagementTools
    Write-Host "IIS has been enabled."
}

Set-ExecutionPolicy Bypass -Scope Process -Force
enable-iss
install-chocolatey
install-dotnet-hosting
install-python3
