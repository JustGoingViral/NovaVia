# Zenodo Release Instructions

This document provides instructions for publishing NOVA ViA releases to Zenodo for permanent archival and DOI assignment.

## Prerequisites

1. **Zenodo Account**: Create an account at https://zenodo.org/ (or use https://sandbox.zenodo.org/ for testing)
2. **GitHub Integration**: Connect your GitHub repository to Zenodo
3. **ORCID (Recommended)**: Register for an ORCID iD at https://orcid.org/ and add it to `.zenodo.json`

## Metadata Files

The repository includes comprehensive metadata files for Zenodo:

### `.zenodo.json`
Primary metadata file used by Zenodo when creating a release. Contains:
- Title and description
- Creators and contributors with ORCID identifiers
- 60+ keywords for discoverability
- Related identifiers (DOIs to cited papers)
- Grant information
- License (GPL-3.0-or-later)
- Communities and subjects

### `CITATION.cff`
Citation File Format for academic citation. Provides:
- Software citation metadata
- Author information
- References to key papers
- Preferred citation format

### `codemeta.json`
CodeMeta metadata following schema.org standards. Includes:
- Software requirements
- Programming language and platform info
- Funding information
- Application category

## Release Process

### Step 1: Prepare the Release

1. **Update VERSION file**:
   ```bash
   echo "1.0.1" > VERSION
   ```

2. **Update version in all metadata files**:
   - `.zenodo.json`: `"version": "1.0.1"`
   - `CITATION.cff`: `version: 1.0.1`
   - `codemeta.json`: `"version": "1.0.1"`
   - `pyproject.toml`: `version = "1.0.1"`
   - `setup.py`: `version="1.0.1"`

3. **Update CHANGELOG.md** with release notes

4. **Add ORCID identifiers** (if available) to `.zenodo.json`:
   ```json
   "creators": [
     {
       "name": "Salinas, Dustin",
       "affiliation": "NOVA ViA Systems",
       "orcid": "0000-0000-0000-0000"
     }
   ]
   ```

### Step 2: Create GitHub Release

1. **Commit all changes**:
   ```bash
   git add .
   git commit -m "Prepare for v1.0.1 release"
   git push
   ```

2. **Create a Git tag**:
   ```bash
   git tag -a v1.0.1 -m "Release version 1.0.1"
   git push origin v1.0.1
   ```

3. **Create GitHub Release**:
   - Go to https://github.com/JustGoingViral/NovaVia/releases/new
   - Select the tag you just created
   - Add release title: "NOVA ViA v1.0.1"
   - Add release notes from CHANGELOG.md
   - Publish release

### Step 3: Zenodo Will Automatically Create DOI

If GitHub-Zenodo integration is enabled:
1. Zenodo automatically detects the new release
2. Creates a new DOI for the release
3. Archives the release permanently

### Step 4: Update DOI in Files

After Zenodo assigns a DOI (e.g., `10.5281/zenodo.1234567`):

1. **Update README.md**:
   ```markdown
   [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1234567.svg)](https://doi.org/10.5281/zenodo.1234567)
   ```

2. **Update CITATION.cff**:
   ```yaml
   doi: "10.5281/zenodo.1234567"
   repository-artifact: "https://zenodo.org/record/1234567"
   ```

3. **Update preferred citation** in README.md BibTeX:
   ```bibtex
   doi = {10.5281/zenodo.1234567}
   ```

4. Commit and push the DOI updates

## First-Time Zenodo Setup

### Enable GitHub-Zenodo Integration

1. **Login to Zenodo**: https://zenodo.org/
2. **Go to GitHub settings**: https://zenodo.org/account/settings/github/
3. **Authorize Zenodo** to access your GitHub account
4. **Find your repository** in the list
5. **Toggle ON** the switch for JustGoingViral/NovaVia
6. **Create a release** on GitHub to trigger first Zenodo archive

### Manual Upload (Alternative)

If not using GitHub integration:

1. **Create a release archive**:
   ```bash
   git archive --format=zip --output=novavia-v1.0.0.zip v1.0.0
   ```

2. **Upload to Zenodo**:
   - Go to https://zenodo.org/deposit/new
   - Upload the ZIP file
   - Zenodo will read `.zenodo.json` for metadata
   - Review and adjust metadata if needed
   - Publish

## Verification

After publishing:

1. **Check DOI resolution**: Visit the DOI URL to ensure it resolves correctly
2. **Verify metadata**: Ensure all fields are correctly displayed on Zenodo
3. **Test citation**: Check that citation formats are generated correctly
4. **Search for keywords**: Verify that the record is discoverable via keyword search

## Best Practices

1. **Version Consistency**: Ensure version numbers match across all files
2. **Semantic Versioning**: Follow semver (MAJOR.MINOR.PATCH)
3. **ORCID Identifiers**: Always include ORCID iDs for proper attribution
4. **Complete Metadata**: Fill in all fields in `.zenodo.json` for maximum discoverability
5. **DOI Updates**: Update DOI badges and citations after each release
6. **Release Notes**: Write comprehensive release notes in CHANGELOG.md

## Resources

- **Zenodo Documentation**: https://help.zenodo.org/
- **Zenodo GitHub Guide**: https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content
- **CITATION.cff Specification**: https://citation-file-format.github.io/
- **CodeMeta Specification**: https://codemeta.github.io/
- **ORCID**: https://orcid.org/

## Support

For questions or issues with Zenodo publication:
- Zenodo Support: https://zenodo.org/support
- Repository Issues: https://github.com/JustGoingViral/NovaVia/issues
- Email: info@novavia.com

---

**Note**: Always test the release process on Zenodo Sandbox (https://sandbox.zenodo.org/) before publishing to production Zenodo.
