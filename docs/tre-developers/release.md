# How to release an AzureTRE version

A release is created when enough changes have been made and the main branch is stable enough.

The process follows these steps:

1. Update `CHANGELOG.md` in a PR with the following:
    1. Rename the top-most verion noted as unreleaed with the version number that makes sense. Note that you don't have to keep the one that is currently in the file as the version number chosen should reflect the changes made (major, minor, etc.)
    1. Create a new section for the next-unreleaed version so that future changes will be placed there.
    1. Run `devops/scripts/list_versions.sh` and include the output in the change log for the version you're about the release
1. Merge the PR
1. Create a GitHub Release
    <!-- markdownlint-disable-next-line MD034 -->
    1. Go to https://github.com/microsoft/AzureTRE/releases/new
    1. Click on `Choose a tag` and type a new one for you version. It should be in the form of `v0.9.2` - note the "v" in the begining.
    1. The release title should be just the version number "0.9.2" in the example above.
    1. Copy the text from the CHANGELOG.md file and paste in the release description.
    1. Include a final line with a link to the full changelog similar to this:
    <!-- markdownlint-disable-next-line MD034 -->
          **Full Changelog**: https://github.com/microsoft/AzureTRE/compare/v0.9.1...v0.9.2
