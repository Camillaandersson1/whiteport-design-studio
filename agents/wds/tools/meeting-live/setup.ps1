# setup.ps1: installerar allt som inspelningen och utskriften behöver på en Windows-dator.
# Del av WDS (agents/wds/tools/meeting-live.md). Går att köra om hur många gånger som helst.
#
#   powershell -ExecutionPolicy Bypass -File <WDS>\agents\wds\tools\meeting-live\setup.ps1 [-Preload]
#
# Gör:
#   1. Python 3 (winget) om det saknas
#   2. Paketen för inspelning och liveutskrift: pyaudiowpatch, faster-whisper, numpy, pillow, python-socketio
#   3. ffmpeg (winget) för skärmvideon
#   4. Intel-grafik: openvino-genai och optimum-intel, så att den grundliga utskriften går på grafikkortet
#   5. Laddar ned KB-Whisper small (liveutskriften) i förväg; -Preload tar också medium och,
#      med Intel-grafik, konverteringen till OpenVINO (några minuter)
#   6. Kontrollerar att inspelningen hittar skärmarna, och säger till om recordings: saknas i ~/.wds/me.md

param([switch]$Preload)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
function Step($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User") }

Step "1. Python"
$py = $null
foreach ($c in @("python", "py")) {
    if (Have $c) {
        try { $v = & $c -c "import sys; print(sys.version_info[0])" 2>$null; if ($v -eq "3") { $py = $c; break } } catch {}
    }
}
if (-not $py) {
    winget install --id Python.Python.3.13 -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $py = "python"
}
& $py --version

Step "2. Paket för inspelning och liveutskrift"
& $py -m pip install --quiet --upgrade pyaudiowpatch faster-whisper numpy pillow "python-socketio[client]"

Step "3. ffmpeg (skärmvideon)"
if (Have "ffmpeg") { Write-Host "finns redan" } else {
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    if (-not (Have "ffmpeg")) { Write-Host "ffmpeg installerat; starta en ny terminal så att det hittas." -ForegroundColor Yellow }
}

Step "4. Grafikkortet"
$gpus = (Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }) -join ", "
Write-Host "Grafik: $gpus"
$intel = $gpus -match "Intel"
if ($intel) {
    & $py -m pip install --quiet --upgrade openvino-genai "optimum-intel[openvino]" "httpcore>=1.0.9"
    & $py -c "import openvino as ov; d = ov.Core().available_devices; print('OpenVINO ser:', d); print('Grafikkortet används' if 'GPU' in d else 'Inget GPU för OpenVINO: processorn används')"
} else {
    Write-Host "Ingen Intel-grafik: den grundliga utskriften går på processorn." -ForegroundColor Yellow
}

Step "5. Modeller"
& $py -c "from faster_whisper import WhisperModel; WhisperModel('KBLab/kb-whisper-small', device='cpu', compute_type='int8'); print('KB-Whisper small klar (liveutskriften)')"
if ($Preload) {
    & $py -c "from faster_whisper import WhisperModel; WhisperModel('KBLab/kb-whisper-medium', device='cpu', compute_type='int8'); print('KB-Whisper medium klar (grundlig utskrift)')"
    if ($intel) {
        & $py -c "import sys; sys.path.insert(0, r'$here'); import refine; print('OpenVINO-modell:', refine.ov_model_dir('KBLab/kb-whisper-medium'))"
    }
} else {
    Write-Host "Medium och OpenVINO-konverteringen laddas första gången refine.py körs (eller kör med -Preload)."
}

Step "6. Kontroll"
& $py (Join-Path $here "local.py") --list-screens
$me = Join-Path $HOME ".wds\me.md"
if (-not (Test-Path $me) -or -not (Select-String -Path $me -Pattern "^recordings:" -Quiet)) {
    Write-Host "Saknas: en rad 'recordings: <mapp>' i $me (privat mapp för ljud och video). Skillen inspelning frågar annars första gången." -ForegroundColor Yellow
} else {
    Write-Host ((Select-String -Path $me -Pattern "^recordings:").Line)
}
Write-Host "`nKlart. Säg 'spela in' till agenten." -ForegroundColor Green
