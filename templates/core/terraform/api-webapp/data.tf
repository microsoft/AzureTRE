data "local_file" "version" {
    filename = "${path.module}/../../../../api_app/_version.py"
}
