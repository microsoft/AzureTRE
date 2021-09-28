locals {
    version                  = replace(replace(data.local_file.version.content, "__version__ = ",""),"\"","")
}