locals {
  images = yamldecode(file("${path.module}/../images.yml"))
}
