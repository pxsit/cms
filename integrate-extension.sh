#!/bin/bash

# CMS Extension Integration Script
# This script integrates the Chrome extension functionality into CMS

echo "CMS Extension Integration Script"
echo "================================"
echo ""

# Check if we're in the correct directory
if [ ! -f "cms/server/contest/templates/base.html" ]; then
    echo "Error: This script must be run from the CMS root directory."
    echo "Please navigate to your CMS installation directory and run this script again."
    exit 1
fi

echo "✓ Found CMS installation directory"

# Backup the original base.html
if [ ! -f "cms/server/contest/templates/base.html.backup" ]; then
    echo "Creating backup of base.html..."
    cp cms/server/contest/templates/base.html cms/server/contest/templates/base.html.backup
    echo "✓ Backup created: base.html.backup"
else
    echo "✓ Backup already exists: base.html.backup"
fi

# Check if files already exist
if [ -f "cms/server/contest/static/css/cms-extension.css" ] &&
   [ -f "cms/server/contest/static/js/cms-extension.js" ]; then
    echo "✓ Extension files already exist"
else
    echo "⚠ Extension files not found. Please ensure the following files exist:"
    echo "  - cms/server/contest/static/css/cms-extension.css"
    echo "  - cms/server/contest/static/js/cms-extension.js"
    echo ""
    echo "If you're running this script after manually creating the files, they should be detected."
fi

# Check if base.html is already modified
if grep -q "cms-extension.css" cms/server/contest/templates/base.html; then
    echo "✓ Base template already includes extension CSS"
else
    echo "⚠ Base template doesn't include extension CSS"
    echo "Please manually add this line to base.html after the existing CSS links:"
    echo '        <link rel="stylesheet" href="{{ url("static", "css", "cms-extension.css") }}">'
fi

if grep -q "cms-extension.js" cms/server/contest/templates/base.html; then
    echo "✓ Base template already includes extension JavaScript"
else
    echo "⚠ Base template doesn't include extension JavaScript"
    echo "Please manually add this line to base.html after the existing script tags:"
    echo '        <script src="{{ url("static", "js", "cms-extension.js") }}"></script>'
fi

echo ""
echo "Integration Status"
echo "=================="

# Check all required files
files=(
    "cms/server/contest/static/css/cms-extension.css"
    "cms/server/contest/static/js/cms-extension.js"
    "cms/server/contest/static/CMS_EXTENSION_README.md"
    "cms/server/contest/static/js/cms-extension-migration.js"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (missing)"
        all_exist=false
    fi
done

echo ""
if [ "$all_exist" = true ]; then
    echo "🎉 Integration complete!"
    echo ""
    echo "What's next:"
    echo "1. No service restart required - the integration works immediately"
    echo "2. Refresh your browser on any CMS contest page to see the new features"
    echo "3. Users can uninstall the Chrome extension (if they had it installed)"
    echo "4. Check the README.md file for detailed documentation"
    echo ""
    echo "Features now available:"
    echo "• Task scores displayed in sidebar with color coding"
    echo "• Total score and percentage displayed"
    echo "• Auto-refresh on submissions"
    echo "• Manual refresh button"
    echo "• Intelligent caching for better performance"
else
    echo "❌ Integration incomplete - some files are missing"
    echo ""
    echo "Please ensure all required files are created before proceeding."
fi

echo ""
echo "For support or issues, refer to the CMS_EXTENSION_README.md file."
