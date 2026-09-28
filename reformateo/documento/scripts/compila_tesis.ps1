# Compila Documentos/FinalTesisV2/tesis.md a PDF (o a Word) con pandoc.
# Punto F5 de la preparación antes de redactar, 2026-09-27; C-222.
#
# Requisitos de esta máquina (ya instalados el 2026-09-27):
#   - pandoc 3.11 (winget JohnMacFarlane.Pandoc; queda en %LOCALAPPDATA%\Pandoc)
#   - MiKTeX 24.1 con XeLaTeX, apuntado al espejo del MIT porque el
#     repositorio por defecto daba «SSL connect error», y con la instalación
#     automática de paquetes activada:
#       initexmf --set-config-value="[MPM]RemoteRepository=https://mirrors.mit.edu/CTAN/systems/win32/miktex/tm/packages/"
#       initexmf --set-config-value="[MPM]AutoInstall=1"
#
# Antes de compilar, la compuerta de vetadas tiene que estar limpia
# (reformateo/documento/scripts/compuerta_vetadas.py): entre otras cosas
# detecta «\,\%» dentro de fórmulas, que rompe babel en español.
#
# Uso (desde la raíz del repositorio):
#   powershell -File reformateo/documento/scripts/compila_tesis.ps1           # PDF
#   powershell -File reformateo/documento/scripts/compila_tesis.ps1 -Word     # .docx
param([switch]$Word, [string]$Salida = "")

$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$tesis = Join-Path $raiz "Documentos\FinalTesisV2"
$bib = Join-Path $raiz "Documentos\references.bib"
$pandoc = Join-Path $env:LOCALAPPDATA "Pandoc\pandoc.exe"
if (-not (Test-Path $pandoc)) { throw "no está pandoc en $pandoc" }
if ($Salida -eq "") {
    $Salida = Join-Path $tesis ($(if ($Word) { "tesis.docx" } else { "tesis.pdf" }))
}
$args = @("tesis.md", "--citeproc", "--bibliography", $bib,
          "--resource-path", $tesis, "-o", $Salida)
if (-not $Word) {
    $args += @("--pdf-engine=xelatex", "-V", "lang=es",
               "-V", "mainfont=Times New Roman")
}
Push-Location $tesis
try {
    & $pandoc @args
    if ($LASTEXITCODE -ne 0) { throw "pandoc salió con código $LASTEXITCODE" }
    Write-Output ("escrito {0} ({1:N0} bytes)" -f $Salida, (Get-Item $Salida).Length)
} finally {
    Pop-Location
}
