# Read The Docs Setup Instructions

This document provides step-by-step instructions for setting up Read The Docs for the iops-profiler project.

## Prerequisites

Before starting, ensure:
- You have admin access to the lincc-frameworks/iops-profiler GitHub repository
- You have a Read The Docs account (sign up at https://readthedocs.org)
- The repository contains the necessary configuration files (already present):
  - `.readthedocs.yml` - Read The Docs configuration
  - `docs/conf.py` - Sphinx configuration
  - `docs/requirements.txt` - Documentation dependencies
  - `docs/` directory with RST files and notebooks

## Step 1: Import the Project to Read The Docs

1. **Log in to Read The Docs**
   - Go to https://readthedocs.org
   - Sign in with your GitHub account

2. **Import the Project**
   - Click on your username in the top right
   - Select "My Projects"
   - Click "Import a Project"
   - Find "lincc-frameworks/iops-profiler" in the list of repositories
   - Click the "+" button next to it
   - If you don't see it, click "Import Manually" and enter:
     - Repository URL: `https://github.com/lincc-frameworks/iops-profiler`
     - Repository type: Git

3. **Configure Project Details**
   - Name: `iops-profiler`
   - Repository URL: `https://github.com/lincc-frameworks/iops-profiler` (auto-filled)
   - Default branch: `main`
   - Default version: `latest`
   - Programming Language: Python
   - Click "Next"

## Step 2: Configure Build Settings

1. **Go to Project Settings**
   - Navigate to your project dashboard
   - Click "Admin" in the left sidebar
   - Click "Settings"

2. **Basic Settings** (Admin → Settings)
   - Project name: `iops-profiler`
   - Repository URL: `https://github.com/lincc-frameworks/iops-profiler`
   - Default branch: `main`
   - Documentation type: `Sphinx Html`
   - Language: `English`
   - Programming Language: `Python`
   - Check "Show versions warning"
   - Save

3. **Advanced Settings** (Admin → Advanced Settings)
   - Default version: `latest`
   - Requirements file: `docs/requirements.txt`
   - Python interpreter: `CPython 3.x`
   - Install Project: ✓ (checked)
   - Save

## Step 3: Configure .readthedocs.yml

The `.readthedocs.yml` file is already configured in the repository with the following settings:

```yaml
version: 2

build:
  os: ubuntu-22.04
  tools:
    python: "3.10"

sphinx:
   configuration: docs/conf.py

python:
   install:
   - requirements: docs/requirements.txt
   - method: pip
     path: .
```

**Key configuration details:**
- Python 3.10 is used (matches project requirements)
- Sphinx configuration is at `docs/conf.py`
- Documentation dependencies from `docs/requirements.txt`
- Project is installed with pip (needed for API documentation)

## Step 4: Trigger the First Build

1. **Manual Build Trigger**
   - Go to "Builds" in the left sidebar
   - Click "Build version: latest"
   - Wait for the build to complete

2. **Check Build Status**
   - The build should succeed (green checkmark)
   - If it fails, click on the build to see the error log
   - Common issues:
     - Missing dependencies → check `docs/requirements.txt`
     - Sphinx errors → check `docs/conf.py`
     - Import errors → ensure package is installed

3. **View the Documentation**
   - Once build succeeds, click "View Docs"
   - Or visit: `https://iops-profiler.readthedocs.io/en/latest/`

## Step 5: Enable Build on Commit

1. **Configure GitHub Webhook** (automatic when importing from GitHub)
   - Admin → Integrations
   - Verify GitHub webhook is present
   - If not, click "Add integration" → "GitHub incoming webhook"

2. **Configure Branch/Tag Settings** (Admin → Versions)
   - Activate versions you want to build:
     - `latest` (latest commit on main branch) - should be active by default
     - `stable` (latest release) - activate this
   - Version settings:
     - Active: Builds and is visible
     - Hidden: Builds but not visible in version selector
     - Public: Accessible without login

## Step 6: Set Up Version Management

1. **Configure Version Settings** (Admin → Versions)
   - **latest**: Keep active - this tracks the main branch
   - **stable**: Activate - this will track tagged releases
   - For each new release tag (e.g., v1.0.0), Read The Docs will automatically create a version

2. **Default Version** (Admin → Advanced Settings)
   - Set "Default version" to `stable` (recommended for production)
   - Or keep as `latest` if you want users to see development docs by default

## Step 7: Add Badge to README (Already Done)

The README.md already includes the documentation badge:

```markdown
[![Documentation Status](https://readthedocs.org/projects/iops-profiler/badge/?version=latest)](https://iops-profiler.readthedocs.io/en/latest/?badge=latest)
```

This badge shows build status and links to the docs.

## Step 8: Configure GitHub Integration (Optional but Recommended)

1. **Enable Pull Request Builds**
   - Admin → Integrations → GitHub incoming webhook
   - Edit webhook
   - Check "Build pull requests for this project"
   - This will build docs for each PR

2. **Configure PR Comments**
   - This allows Read The Docs to comment on PRs with doc preview links
   - Requires Read The Docs GitHub app installation
   - Follow prompts in Admin → Integrations

## Verification Checklist

After setup, verify:

- [ ] Project appears in your Read The Docs dashboard
- [ ] Initial build completed successfully
- [ ] Documentation is viewable at https://iops-profiler.readthedocs.io/
- [ ] All pages render correctly:
  - [ ] Home page
  - [ ] Introduction
  - [ ] Installation guide
  - [ ] User guide
  - [ ] Example notebooks (3 notebooks)
  - [ ] Platform notes
  - [ ] Troubleshooting
  - [ ] API reference
- [ ] Notebooks execute and render properly
- [ ] Images display correctly
- [ ] Code blocks are formatted properly
- [ ] Navigation works (sidebar, breadcrumbs)
- [ ] Search functionality works
- [ ] GitHub webhook is configured (builds trigger on push)
- [ ] Documentation badge in README is working

## Ongoing Maintenance

### When to Rebuild Docs

Documentation rebuilds automatically when:
- Code is pushed to main branch
- A new tag/release is created
- A pull request is opened (if PR builds are enabled)

### Manual Rebuild

To manually rebuild:
1. Go to "Builds" in project dashboard
2. Click "Build version: latest" (or specific version)

### Updating Documentation

To update docs:
1. Edit files in `docs/` directory
2. Commit and push to main branch
3. Read The Docs automatically rebuilds

### Troubleshooting Builds

If a build fails:
1. Check build logs in Read The Docs dashboard
2. Common issues:
   - Missing dependencies: Update `docs/requirements.txt`
   - Sphinx errors: Check RST syntax in docs files
   - Notebook errors: Ensure notebooks can execute cleanly
   - Import errors: Verify package installation in `.readthedocs.yml`

### Updating Python Version

To update Python version:
1. Edit `.readthedocs.yml`
2. Change `python: "3.10"` to desired version
3. Commit and push

## Support

- Read The Docs Documentation: https://docs.readthedocs.io/
- Sphinx Documentation: https://www.sphinx-doc.org/
- nbsphinx Documentation: https://nbsphinx.readthedocs.io/

## Summary

The iops-profiler documentation is now set up with:

- ✅ Comprehensive user documentation (7 pages)
- ✅ 3 example notebooks demonstrating key features
- ✅ Automatic API reference generation
- ✅ Automatic builds on push
- ✅ Version management for releases
- ✅ Clean, professional theme (Read The Docs theme)
- ✅ Search functionality
- ✅ Badge in README

The documentation URL is: **https://iops-profiler.readthedocs.io/**
