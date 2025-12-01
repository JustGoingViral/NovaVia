# Release Process Guide

This document describes the process for creating releases of the NOVA ViA platform.

## Release Checklist

### Pre-Release

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated with new version
- [ ] VERSION file updated
- [ ] All PRs merged to main branch
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Performance benchmarks validated

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.0.0)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Creating a Release

#### Option 1: Using the Release Script

```bash
# Make sure you're on the main branch
git checkout main
git pull origin main

# Run the release script
./scripts/create_release.sh v1.0.0

# Follow the instructions to create the GitHub release
```

#### Option 2: Manual Process

1. **Update Version Files**
   ```bash
   # Update VERSION file
   echo "1.0.0" > VERSION
   
   # Update setup.py
   # Update pyproject.toml
   # Update __init__.py files with __version__
   ```

2. **Update Documentation**
   ```bash
   # Update CHANGELOG.md with new version section
   # Update RELEASE_NOTES.md if creating major release
   ```

3. **Commit Changes**
   ```bash
   git add VERSION CHANGELOG.md
   git commit -m "Bump version to v1.0.0"
   git push origin main
   ```

4. **Create Git Tag**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0

   Features:
   - ANEP system with device orchestration
   - IRIP multi-agent framework
   - Complete API gateway
   - Docker deployment support
   
   See CHANGELOG.md for full details."
   
   git push origin v1.0.0
   ```

5. **Create GitHub Release**
   
   Using GitHub CLI:
   ```bash
   gh release create v1.0.0 \
     --title "NOVA ViA v1.0.0" \
     --notes-file RELEASE_NOTES.md
   ```
   
   Or manually:
   - Go to https://github.com/JustGoingViral/NovaVia/releases/new
   - Select tag: v1.0.0
   - Release title: NOVA ViA v1.0.0
   - Copy content from RELEASE_NOTES.md
   - Attach any release assets
   - Click "Publish release"

### Post-Release

1. **Verify Release**
   ```bash
   # Check release is visible
   gh release view v1.0.0
   
   # Test installation
   pip install git+https://github.com/JustGoingViral/NovaVia.git@v1.0.0
   ```

2. **Update Documentation**
   - Update main README.md with latest release info
   - Update installation instructions if needed
   - Announce release on relevant channels

3. **Create Next Development Version**
   ```bash
   # Start work on next version
   git checkout -b develop/v1.1.0
   
   # Update VERSION to next version with -dev suffix
   echo "1.1.0-dev" > VERSION
   
   # Commit and push
   git add VERSION
   git commit -m "Start development of v1.1.0"
   git push origin develop/v1.1.0
   ```

## Release Types

### Major Release (X.0.0)
- Significant new features
- Breaking changes
- Major architectural changes
- Update RELEASE_NOTES.md with detailed information
- Consider beta/RC releases first

### Minor Release (x.Y.0)
- New features (backwards compatible)
- Performance improvements
- Non-breaking enhancements
- Update CHANGELOG.md

### Patch Release (x.y.Z)
- Bug fixes
- Security patches
- Documentation updates
- Quick turnaround, minimal testing

## Release Assets

### Files to Include in GitHub Release

1. **Source Code** (automatically included by GitHub)
   - Source code (zip)
   - Source code (tar.gz)

2. **Documentation** (reference in release notes)
   - CHANGELOG.md
   - RELEASE_NOTES.md
   - README.md
   - DEVELOPMENT_ROADMAP.md

3. **Docker Images** (optional, for major releases)
   - Build and push to Docker Hub
   - Include docker-compose.yml

## Versioning Strategy

### Development Versions
- Use `-dev` suffix: `1.1.0-dev`
- Indicates work in progress

### Pre-release Versions
- Alpha: `1.0.0-alpha.1`
- Beta: `1.0.0-beta.1`
- Release Candidate: `1.0.0-rc.1`

### Stable Versions
- Production ready: `1.0.0`
- No suffix, clean version number

## Testing Before Release

### Required Tests
```bash
# Run all tests
pytest tests/ -v

# Check code quality
black --check .
isort --check-only .
pylint anep irip api

# Type checking
mypy anep irip api

# Security scan
bandit -r anep irip api

# Build package
python -m build
```

### Integration Tests
```bash
# Start infrastructure
docker-compose up -d

# Run integration tests
pytest tests/integration/ -v

# Test API endpoints
python -m pytest tests/api/ -v

# Cleanup
docker-compose down
```

### Demo Verification
```bash
# Run demo to verify core functionality
python demo_device_orchestration.py
```

## Rollback Procedure

If a release has critical issues:

1. **Delete the Release**
   ```bash
   gh release delete v1.0.0 --yes
   ```

2. **Delete the Tag**
   ```bash
   git tag -d v1.0.0
   git push origin :refs/tags/v1.0.0
   ```

3. **Fix the Issue**
   ```bash
   # Fix the critical issue
   git commit -m "Fix critical issue in v1.0.0"
   git push origin main
   ```

4. **Create Patch Release**
   ```bash
   # Create v1.0.1 instead
   ./scripts/create_release.sh v1.0.1
   ```

## Communication

### Release Announcement Template

```markdown
# NOVA ViA v1.0.0 Released! 🎉

We're excited to announce the release of NOVA ViA v1.0.0!

## Highlights
- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## Installation
pip install git+https://github.com/JustGoingViral/NovaVia.git@v1.0.0

## Documentation
- Release Notes: https://github.com/JustGoingViral/NovaVia/releases/tag/v1.0.0
- Full Changelog: https://github.com/JustGoingViral/NovaVia/blob/main/CHANGELOG.md

## Feedback
Please report any issues: https://github.com/JustGoingViral/NovaVia/issues
```

## Automation (Future)

Consider automating releases with GitHub Actions:

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags:
      - 'v*'
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Create Release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body_path: RELEASE_NOTES.md
```

## Support

For questions about the release process:
- Open an issue: https://github.com/JustGoingViral/NovaVia/issues
- Email: info@novavia.com

---

**Last Updated:** December 2024
