$ErrorActionPreference = 'Continue'

$projectPath = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$logDir = Join-Path $projectPath 'logs'
$logFile = Join-Path $logDir 'alertas_aso_scheduler.log'

if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory | Out-Null
}

Push-Location $projectPath
try {
    "[$timestamp] Inicio execucao notificar_alertas_aso" | Out-File -FilePath $logFile -Append -Encoding utf8
    cmd /c "py manage.py notificar_alertas_aso --canal ambos 2>&1" | Out-File -FilePath $logFile -Append -Encoding utf8
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ExitCode=$LASTEXITCODE" | Out-File -FilePath $logFile -Append -Encoding utf8
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Fim execucao`n" | Out-File -FilePath $logFile -Append -Encoding utf8
}
finally {
    Pop-Location
}
