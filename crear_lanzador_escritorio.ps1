$ErrorActionPreference = "Stop"

$raizProyecto = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonConfigurado = Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\python.exe"
$python = if (Test-Path -LiteralPath $pythonConfigurado) {
    $pythonConfigurado
} else {
    $comandoPython = Get-Command python -ErrorAction SilentlyContinue
    if ($comandoPython) { $comandoPython.Source } else { $null }
}

if (-not $python) {
    throw "No se encontró Python. Define la ruta de Python en el script o agrega Python al PATH."
}

$entornoBuild = Join-Path $raizProyecto ".venv-lanzador"
$pythonBuild = Join-Path $entornoBuild "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonBuild)) {
    & $python -m venv --system-site-packages $entornoBuild
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno local para construir el ejecutable." }
}

& $pythonBuild -m pip install -r (Join-Path $raizProyecto "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de construcción." }

& $pythonBuild (Join-Path $raizProyecto "crear_icono_pandora.py")
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el icono transparente de Pandora." }

$salida = Join-Path $raizProyecto "dist"
$trabajo = Join-Path $raizProyecto "build\pyinstaller"
& $pythonBuild -m PyInstaller --noconfirm --distpath $salida --workpath $trabajo (Join-Path $raizProyecto "lanzador_pandora.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo crear PandoraEjecutor.exe." }

$ejecutable = Join-Path $salida "PandoraEjecutor.exe"
if (-not (Test-Path -LiteralPath $ejecutable)) {
    throw "No se encontró el ejecutable generado: $ejecutable"
}

$escritorio = [Environment]::GetFolderPath("Desktop")
$rutaAccesoDirecto = Join-Path $escritorio "Pandora.lnk"
$shell = New-Object -ComObject WScript.Shell
$accesoDirecto = $shell.CreateShortcut($rutaAccesoDirecto)
$accesoDirecto.TargetPath = $ejecutable
$accesoDirecto.WorkingDirectory = $raizProyecto
$accesoDirecto.Description = "Abrir el centro de ejecución de Pandora"
$accesoDirecto.IconLocation = "$(Join-Path $raizProyecto 'assets\pandora-tesoro.ico'),0"
$accesoDirecto.Save()

Write-Host "Ejecutable creado: $ejecutable"
Write-Host "Acceso directo creado: $rutaAccesoDirecto"
