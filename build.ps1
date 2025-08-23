# build.ps1
$ErrorActionPreference = "Stop"

param(
  [switch]$CleanAppData,  # usage: .\build.ps1 -CleanAppData
  [switch]$Install        # usage: .\build.ps1 -Install  (auto-runs the installer after building)
)

# --- Config ---
$Inno = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
$AppDataDir = Join-Path $env:APPDATA "GUI Scale Drawing"
$VersionFile = Join-Path $PSScriptRoot "VERSION"
$SpecVersion = "1.0.0"   # fallback if VERSION missing
$GuiFile     = Join-Path $PSScriptRoot "gui_main_menu.py"

# --- Read version for naming (independent of runtime APP_VERSION) ---
if (Test-Path $VersionFile) {
  $version = (Get-Content -Raw $VersionFile).Trim()
} else {
  Write-Warning "VERSION file not found. Falling back to $SpecVersion"
  $version = $SpecVersion
}
Write-Host "Building ScaleDrawing v$version" -ForegroundColor Cyan

# --- Sanity check APP_VERSION inside gui_main_menu.py ---
if (Test-Path $GuiFile) {
  $line = Select-String -Path $GuiFile -Pattern 'APP_VERSION\s*=\s*"(.+)"' | Select-Object -First 1
  if ($line) {
    $appVerMatch = [regex]::Match($line.Line, 'APP_VERSION\s*=\s*"(.+)"')
    if ($appVerMatch.Success) {
      $appVer = $appVerMatch.Groups[1].Value
      if ($appVer -ne $version) {
        Write-Warning "VERSION mismatch! VERSION file = $version, gui_main_menu.py = $appVer"
      }
    }
  } else {
    Write-Warning "Could not find APP_VERSION in gui_main_menu.py"
  }
} else {
  Write-Warning "gui_main_menu.py not found at $GuiFile"
}

# --- Optional: clean per-user AppData for a truly fresh run ---
if ($CleanAppData) {
  if (Test-Path $AppDataDir) {
    Write-Host "Cleaning AppData: $AppDataDir"
    Remove-Item -Recurse -Force $AppDataDir -ErrorAction SilentlyContinue
  }
}

# --- Cleanup previous outputs ---
Write-Host "Cleaning build/, dist/, and current-version installer"
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item "setup_gui_scale_drawing_$version.exe" -Force -ErrorAction SilentlyContinue

# --- (Optional) sync version_info.txt numerals used by PyInstaller metadata ---
if (Test-Path ".\version_info.txt") {
  (Get-Content .\version_info.txt) -replace '^\s*FileVersion\s*=\s*".*"$', "FileVersion = `"$version`"" `
                                   -replace '^\s*ProductVersion\s*=\s*".*"$', "ProductVersion = `"$version`"" `
  | Set-Content .\version_info.txt
}

# --- Build EXE with PyInstaller ---
Write-Host "Running PyInstaller…" -ForegroundColor Yellow
pyinstaller --noconfirm --onefile --windowed `
  --name "ScaleDrawing" `
  --icon gui_icon.ico `
  --version-file version_info.txt `
  gui_main_menu.py

if (!(Test-Path ".\dist\ScaleDrawing.exe")) {
  throw "PyInstaller did not produce dist\ScaleDrawing.exe"
}

# --- Build installer with Inno Setup ---
if (!(Test-Path $Inno)) { throw "Inno Setup not found at $Inno" }
Write-Host "Compiling installer…" -ForegroundColor Yellow
& $Inno ".\installer_script.iss"

$installer = ".\setup_gui_scale_drawing_$version.exe"
if (!(Test-Path $installer)) {
  throw "Installer not created: $installer"
}

# --- Stage deliverables ---
$releaseDir = Join-Path $PSScriptRoot "Releases\$version"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
Copy-Item ".\dist\ScaleDrawing.exe" $releaseDir -Force
Copy-Item $installer $releaseDir -Force -ErrorAction SilentlyContinue
if (Test-Path ".\CHANGELOG.md") { Copy-Item ".\CHANGELOG.md" $releaseDir -Force }
if (Test-Path ".\README.md")    { Copy-Item ".\README.md"    $releaseDir -Force }

Write-Host ""
Write-Host "✅ Build complete!" -ForegroundColor Green
Write-Host "   EXE:        .\dist\ScaleDrawing.exe"
Write-Host "   Installer:  $installer"
Write-Host "   Releases:   $releaseDir"
Write-Host ""

# --- Optional: auto-run installer ---
if ($Install) {
  Write-Host "Launching installer…" -ForegroundColor Yellow
  Start-Process -FilePath $installer
}

