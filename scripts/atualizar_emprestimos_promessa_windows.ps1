$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$pythonExe = "C:/Users/compras1.tbrasilis/AppData/Local/Programs/Python/Python313/python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python nao encontrado em: $pythonExe"
}

Set-Location $projectRoot

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Iniciando atualizacao de promessas de emprestimos" | Out-File -FilePath "logs/emprestimos_promessa_scheduler.log" -Append -Encoding utf8

& $pythonExe manage.py atualizar_emprestimos_promessa --quiet *>> "logs/emprestimos_promessa_scheduler.log"

$timestampFim = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestampFim] Finalizado" | Out-File -FilePath "logs/emprestimos_promessa_scheduler.log" -Append -Encoding utf8
