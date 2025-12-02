# v1.0.0 Release Instructions

This document contains final instructions for creating the official v1.0.0 release of NOVA ViA.

## ✅ Completed Preparation

All necessary files have been created and tested:

### Documentation Files
- ✅ **CHANGELOG.md** - Complete changelog with all v1.0.0 features
- ✅ **RELEASE_NOTES.md** - Detailed release announcement
- ✅ **RELEASING.md** - Process guide for future releases
- ✅ **VERSION** - Version file (1.0.0)

### Packaging Files
- ✅ **setup.py** - Python package configuration
- ✅ **pyproject.toml** - Modern packaging configuration
- ✅ **MANIFEST.in** - Distribution file specification
- ✅ **__init__.py** - Added to all packages (anep, irip, api, config, data)

### Automation
- ✅ **scripts/create_release.sh** - Release automation script

### Quality Checks
- ✅ Package builds successfully (tested with `python -m build`)
- ✅ Code review completed and feedback addressed
- ✅ Security scan passed (0 vulnerabilities)
- ✅ All files committed and pushed to branch

## 🚀 Creating the GitHub Release

### Option 1: After PR Merge (Recommended)

1. **Merge this PR to main branch**
   ```bash
   # After PR approval and merge to main
   git checkout main
   git pull origin main
   ```

2. **Run the release script**
   ```bash
   ./scripts/create_release.sh v1.0.0
   ```

3. **Create GitHub Release**
   
   The script will output instructions. Use GitHub CLI:
   ```bash
   gh release create v1.0.0 \
     --title "NOVA ViA v1.0.0 - Initial Release 🌟" \
     --notes-file RELEASE_NOTES.md
   ```
   
   Or manually at: https://github.com/JustGoingViral/NovaVia/releases/new

### Option 2: Manual Process

If you prefer to create the release manually:

1. **Create Git Tag**
   ```bash
   git checkout main
   git pull origin main
   
   git tag -a v1.0.0 -m "NOVA ViA v1.0.0 - Initial Release

   Revolutionary AI-powered platform for addiction recovery through
   neuroplasticity-based treatment.

   Key Features:
   - ANEP: Adaptive Neuroplasticity Enhancement Protocol
   - IRIP: Integrated Recovery Intelligence Platform  
   - Complete API Gateway with HIPAA compliance
   - Docker deployment configuration
   - Comprehensive documentation

   See CHANGELOG.md and RELEASE_NOTES.md for full details."
   ```

2. **Push Tag**
   ```bash
   git push origin v1.0.0
   ```

3. **Create GitHub Release**
   - Go to: https://github.com/JustGoingViral/NovaVia/releases/new
   - Select tag: `v1.0.0`
   - Release title: `NOVA ViA v1.0.0 - Initial Release 🌟`
   - Copy the content from `RELEASE_NOTES.md` into the description
   - Optionally attach build artifacts from `dist/` folder
   - Check "Set as the latest release"
   - Click "Publish release"

## 📦 Release Artifacts

The following distribution files can be attached to the release:

```bash
# Build the distribution packages
python -m build

# Files will be in dist/
# - novavia-1.0.0.tar.gz (source distribution)
# - novavia-1.0.0-py3-none-any.whl (wheel distribution)
```

These files allow users to install via:
```bash
pip install novavia-1.0.0-py3-none-any.whl
# or
pip install novavia-1.0.0.tar.gz
# or from GitHub
pip install git+https://github.com/JustGoingViral/NovaVia.git@v1.0.0
```

## 📢 Post-Release Actions

After creating the release:

1. **Verify Release**
   ```bash
   # Check the release is visible
   gh release view v1.0.0
   
   # Or visit
   # https://github.com/JustGoingViral/NovaVia/releases
   ```

2. **Test Installation**
   ```bash
   # In a fresh environment
   pip install git+https://github.com/JustGoingViral/NovaVia.git@v1.0.0
   ```

3. **Announce the Release**
   - Share on social media
   - Post to relevant communities
   - Notify stakeholders
   - Update project website

4. **Monitor for Issues**
   - Watch for bug reports
   - Respond to questions
   - Plan for patch releases if needed

## 📋 Release Checklist

Before making the release public, verify:

- [ ] All tests pass
- [ ] Documentation is up to date
- [ ] CHANGELOG.md includes all changes
- [ ] Version numbers are correct (1.0.0)
- [ ] Build artifacts are generated successfully
- [ ] Code review completed
- [ ] Security scan passed
- [ ] Demo works correctly (`python demo_device_orchestration.py`)
- [ ] Docker compose starts successfully (`docker-compose up -d`)

## 🆘 Troubleshooting

### If the tag creation fails
```bash
# Check if tag already exists
git tag -l | grep v1.0.0

# If it exists and needs to be recreated
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0

# Then create it again
```

### If the build fails
```bash
# Clean build artifacts
rm -rf build/ dist/ *.egg-info

# Rebuild
python -m build
```

### If there are issues after release
- See RELEASING.md for rollback procedures
- Create a patch release (v1.0.1) with fixes

## 📚 Additional Resources

- **Full Release Guide**: [RELEASING.md](RELEASING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Release Notes**: [RELEASE_NOTES.md](RELEASE_NOTES.md)
- **Main Documentation**: [README.md](README.md)
- **Development Roadmap**: [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)

## 🎉 Success!

Once the release is published:
- Users can install NOVA ViA via pip
- The platform is officially version 1.0.0
- A stable baseline is established for future development
- The project has professional packaging and distribution

**Every Brain Can Heal. Every Life Can Change.** 🌟

---

For questions or issues with the release process:
- Open an issue: https://github.com/JustGoingViral/NovaVia/issues
- Email: info@novavia.com
