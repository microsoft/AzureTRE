# How to release an AzureTRE version

A release is created when enough changes have been made and the main branch is stable enough.

The process follows these steps:

1. Create a `Prep for Release v0...` issue to track.
2. Create a new branch for the release prep and open in Dev Container.
3. Update `CHANGELOG.md` in a PR with the following:
   1. Rename the top-most version noted as unreleased with the version number that makes sense. Note that you don't have to keep the one that is currently in the file as the version number chosen should reflect the changes made (major, minor, etc.).
   2. Create a new section for the next-unreleased version so that future changes will be placed there.
   3. Run `devops/scripts/list_versions.sh` and include the output in the change log for the version you're about the release.
4. Create PR and link to the `Prep...` issue.
5. Merge the PR.
6. Create GitHub Release in `Pre Release` state.
   <!-- markdownlint-disable-next-line MD034 -->
   1. Go to https://github.com/microsoft/AzureTRE/releases/new
   2. Click on `Choose a tag` and type a new one for you version. It should be in the form of `v0.9.2` - note the "v" in the beginning.
   3. The release title should be just the version number "0.9.2" in the example above.
   4. Copy the text from the CHANGELOG.md file and paste in the release description.
   5. Include a final line with a link to the full changelog similar to this:
   <!-- markdownlint-disable-next-line MD034 -->
      **Full Changelog**: https://github.com/microsoft/AzureTRE/compare/v0.9.1...v0.9.2

7. Update [AzureTRE-Deployment](https://github.com/microsoft/AzureTRE-Deployment). The procedure may vary depending on the level of changes introduced in the new version but should include the following steps:
   1. Update the tag used in [devcontainer.json](https://github.com/microsoft/AzureTRE-Deployment/blob/main/.devcontainer/devcontainer.json).
   2. Rebuild the container.
   3. Compare both `.devcontainer` and `.github` folders of the new release with the ones in the repo and make required updates so that only required difference exist.
   The compare can be done with VSCode [Compare Folders extension](https://marketplace.visualstudio.com/items?itemName=moshfeu.compare-folders) as you have both the old version (under to root folder) and the "new" one inside the _AzureTRE_ symlink.
   4. With all changes made, rebuild the container to verify it's working and that AzureTRE folder has been populated correctly.
8. Once tests have been complete edit GitHub Release by disabling `Set as a pre-release` and enabling `Set as the latest release`.
