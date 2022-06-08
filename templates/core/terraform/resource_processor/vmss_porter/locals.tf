locals {
  version = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
}
