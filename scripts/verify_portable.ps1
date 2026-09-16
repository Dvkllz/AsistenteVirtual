param([string]$Executable = (Join-Path $PSScriptRoot '../dist/AsistenteVirtual.exe'))
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = (Resolve-Path -LiteralPath $Executable).Path
$checkRoot = Join-Path $projectRoot ('artifacts/portable check ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $checkRoot | Out-Null
$copy = Join-Path $checkRoot 'AsistenteVirtual.exe'
Copy-Item -LiteralPath $source -Destination $copy
$report = Join-Path $checkRoot 'informe.json'
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $copy
$startInfo.WorkingDirectory = $checkRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$startInfo.ArgumentList.Add('--self-test')
$startInfo.ArgumentList.Add($report)
foreach ($name in @('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'OPENAI_API_KEY', 'OPENAI_MODEL',
                    'OPENAI_BASE_URL', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
                    'QML2_IMPORT_PATH', 'QML_IMPORT_PATH')) {
    $startInfo.Environment.Remove($name) | Out-Null
}
$startInfo.Environment['PATH'] = Join-Path $env:SystemRoot 'System32'
$startInfo.Environment['QT_QPA_PLATFORM'] = 'windows'
$timer = [System.Diagnostics.Stopwatch]::StartNew()
$checkProcess = [System.Diagnostics.Process]::Start($startInfo)
if (-not $checkProcess.WaitForExit(60000)) {
    throw "La comprobacion sigue abierta (PID $($checkProcess.Id)); informe esperado: $report"
}
$timer.Stop()
if ($checkProcess.ExitCode -ne 0) { throw "Fallo la comprobacion; revisa $report" }
$result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
if (-not $result.ok -or -not $result.frozen) { throw "Informe portable no valido: $report" }
Write-Output "Ejecutable independiente verificado. Tiempo total: $([Math]::Round($timer.Elapsed.TotalSeconds, 1)) s"
Write-Output "Informe: $report"
Write-Output ($result | ConvertTo-Json -Depth 3)
