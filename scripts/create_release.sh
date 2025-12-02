#!/bin/bash
# NOVA ViA Release Creation Script
set -e
VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v1.0.0"
    exit 1
fi
echo "Creating release $VERSION for NOVA ViA"
git tag -a "$VERSION" -m "NOVA ViA Release $VERSION"
git push origin "$VERSION"
echo "✅ Git tag created and pushed successfully!"
echo "Use: gh release create $VERSION --title 'NOVA ViA $VERSION' --notes-file RELEASE_NOTES.md"
