@echo off
setlocal enabledelayedexpansion

echo CMS Extension Integration Script
echo ================================
echo.

REM Check if we're in the correct directory
if not exist "cms\server\contest\templates\base.html" (
    echo Error: This script must be run from the CMS root directory.
    echo Please navigate to your CMS installation directory and run this script again.
    pause
    exit /b 1
)

echo ✓ Found CMS installation directory

REM Create backup of original base.html
if not exist "cms\server\contest\templates\base.html.backup" (
    echo Creating backup of base.html...
    copy "cms\server\contest\templates\base.html" "cms\server\contest\templates\base.html.backup" >nul
    echo ✓ Backup created: base.html.backup
) else (
    echo ✓ Backup already exists: base.html.backup
)

REM Check if files already exist
set "files_exist=true"
if exist "cms\server\contest\static\css\cms-extension.css" (
    if exist "cms\server\contest\static\js\cms-extension.js" (
        echo ✓ Extension files already exist
    ) else (
        set "files_exist=false"
    )
) else (
    set "files_exist=false"
)

if "!files_exist!"=="false" (
    echo ⚠ Extension files not found. Please ensure the following files exist:
    echo   - cms\server\contest\static\css\cms-extension.css
    echo   - cms\server\contest\static\js\cms-extension.js
    echo.
    echo If you're running this script after manually creating the files, they should be detected.
)

REM Check if base.html is already modified
findstr /c:"cms-extension.css" "cms\server\contest\templates\base.html" >nul
if !errorlevel! equ 0 (
    echo ✓ Base template already includes extension CSS
) else (
    echo ⚠ Base template doesn't include extension CSS
    echo Please manually add this line to base.html after the existing CSS links:
    echo         ^<link rel="stylesheet" href="{{ url("static", "css", "cms-extension.css") }}"^>
)

findstr /c:"cms-extension.js" "cms\server\contest\templates\base.html" >nul
if !errorlevel! equ 0 (
    echo ✓ Base template already includes extension JavaScript
) else (
    echo ⚠ Base template doesn't include extension JavaScript
    echo Please manually add this line to base.html after the existing script tags:
    echo         ^<script src="{{ url("static", "js", "cms-extension.js") }}"^>^</script^>
)

echo.
echo Integration Status
echo ==================

REM Check all required files
set "all_exist=true"
set "files[0]=cms\server\contest\static\css\cms-extension.css"
set "files[1]=cms\server\contest\static\js\cms-extension.js"
set "files[2]=cms\server\contest\static\CMS_EXTENSION_README.md"
set "files[3]=cms\server\contest\static\js\cms-extension-migration.js"

for /l %%i in (0,1,3) do (
    if exist "!files[%%i]!" (
        echo ✓ !files[%%i]!
    ) else (
        echo ✗ !files[%%i]! ^(missing^)
        set "all_exist=false"
    )
)

echo.
if "!all_exist!"=="true" (
    echo 🎉 Integration complete!
    echo.
    echo What's next:
    echo 1. No service restart required - the integration works immediately
    echo 2. Refresh your browser on any CMS contest page to see the new features
    echo 3. Users can uninstall the Chrome extension ^(if they had it installed^)
    echo 4. Check the README.md file for detailed documentation
    echo.
    echo Features now available:
    echo • Task scores displayed in sidebar with color coding
    echo • Total score and percentage displayed
    echo • Auto-refresh on submissions
    echo • Manual refresh button
    echo • Intelligent caching for better performance
) else (
    echo ❌ Integration incomplete - some files are missing
    echo.
    echo Please ensure all required files are created before proceeding.
)

echo.
echo For support or issues, refer to the CMS_EXTENSION_README.md file.
echo.
pause
