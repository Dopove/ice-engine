# BSL-1.1 License Application — Verification Complete

## Summary
Verified that BSL-1.1 (Business Source License 1.1) has been applied to all three community OSS branches requested in issue 01a1dae8-1514-71c3-83f0-fd527657af51.

## Verification Results

### 1. Community Branch (`community`)
- **LICENSE**: Full BSL-1.1 text present at repo root (4253 bytes)
- **pyproject.toml**: 
  - `license = {text = "BSL-1.1"}`
  - Classifier: `"License :: Other/Proprietary License"`
- **.gitlab-ci.yml**: Publish stage with two jobs:
  - `publish:pypi` — triggers on tags matching `^v.*-community$`, builds wheels, uploads to PyPI via `TWINE_PASSWORD`
  - `publish:github` — triggers on same tags, mirrors to GitHub via `GITHUB_TOKEN`

### 2. OSS Branch (`oss`)
- **LICENSE**: Full BSL-1.1 text present at repo root (4253 bytes)
- **pyproject.toml**:
  - `license = {text = "BSL-1.1"}`
  - Classifier: `"License :: Other/Proprietary License"`
- **.gitlab-ci.yml**: Full pipeline including publish stage with jobs triggering on tags matching `^v.*-oss$`

### 3. Benchmarks Branch (`benchmarks`)
- **LICENSE**: Full BSL-1.1 text present at repo root (4253 bytes)
- **pyproject.toml** (root):
  - `license = {text = "BSL-1.1"}`
  - Classifier: `"License :: Other/Proprietary License"`
- **ice_nexus/pyproject.toml** (sub-package):
  - `license = {text = "BSL-1.1"}`
  - Classifier: `"License :: Other/Proprietary License"`
- **.gitlab-ci.yml**: Publish stage with jobs triggering on tags matching `^v.*-benchmarks$`

## BSL-1.1 Parameters (All Branches)
- **Licensor**: Dopove Private Limited
- **Licensed Work**: Indexless Context Engine (ICE)
- **Additional Use Grant**: Allows commercial use, embedding, self-hosting; blocks redistribution as competing managed memory service
- **Change Date**: 4th anniversary of first public availability
- **Change License**: GNU General Public License v3.0 or later (GPL-3.0-or-later)

## Acceptance Criteria Met
- ✅ BSL-1.1 license applied to community, oss, and benchmarks branches
- ✅ LICENSE.txt added with full BSL-1.1 text on each branch
- ✅ GitLab publish stage added with tag-triggered PyPI publish and GitHub mirror

## Status
Issue set to `in_review` — awaiting review chain (Faye → Jimbei → Founder).