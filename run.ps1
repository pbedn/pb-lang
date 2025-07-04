# notepad $PROFILE
# Set-Alias run "<path>\pb-lang\run.ps1"

param (
    [string]$SourceFile
)

$env:PYTHONBREAKPOINT = "ipdb.set_trace"

if (-not $SourceFile) {
    Write-Host "Usage: .\run.ps1 <path_to_file>"
    exit 1
}

if (-not (Test-Path $SourceFile)) {
    Write-Host "File does not exist: $SourceFile"
    exit 1
}

Write-Host "Run: python run.py toc '$SourceFile' -dr"
python run.py run "$SourceFile" -dr
