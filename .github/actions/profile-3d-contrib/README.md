# profile-3d-contrib (patched copy)

Copy of [yoshi389111/github-profile-3d-contrib](https://github.com/yoshi389111/github-profile-3d-contrib) v0.9.3 (MIT, see LICENSE).

Changes in `dist/index.js` (search for `[feroz-afm patch]`):
- the language donut shows **every** detected language instead of the top 5
- no grey **"other"** slice — commits in repositories without a detected language are left out
- each language label shows its **% share**
- the legend grows so all languages fit

Languages come from each repository's primary language. Private repositories are only counted
when the `PROFILE_3D_TOKEN` secret (classic PAT with `repo` + `read:user`) is set.
