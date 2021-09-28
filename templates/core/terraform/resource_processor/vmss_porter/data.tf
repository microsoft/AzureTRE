data "local_file" "version" {
    filename = "${path.module}/../../../../resource_processor/version.txt"
}