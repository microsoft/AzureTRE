from mock import patch
import logging
from shared.logging import shell_output_logger, chunk_log_output


@patch("shared.logging.logger")
def test_shell_output_logger_empty_console_output(mock_logger):
    shell_output_logger("", "prefix", logging.DEBUG)
    mock_logger.debug.assert_called_once_with("shell console output is empty.")


@patch("shared.logging.logger")
def test_shell_output_logger_image_not_present_locally(mock_logger):
    console_output = "Unable to find image 'test_image' locally\nexecution completed successfully!"
    shell_output_logger(console_output, "prefix", logging.DEBUG)
    mock_logger.debug.assert_called_with("Image not present locally, removing text from console output.")
    mock_logger.log.assert_called_with(logging.INFO, "prefix execution completed successfully!")


@patch("shared.logging.logger")
def test_shell_output_logger_execution_completed_successfully(mock_logger):
    console_output = "execution completed successfully!"
    shell_output_logger(console_output, "prefix", logging.DEBUG)
    mock_logger.log.assert_called_with(logging.INFO, "prefix execution completed successfully!")


@patch("shared.logging.logger")
def test_shell_output_logger_normal_case(mock_logger):
    console_output = "Some logs"
    shell_output_logger(console_output, "prefix", logging.DEBUG)
    mock_logger.log.assert_called_with(logging.DEBUG, "prefix Some logs")


@patch("shared.logging.logger")
def test_shell_output_logger_chunked_logging(mock_logger):
    console_output = "A" * 60000  # 60,000 characters long
    shell_output_logger(console_output, "prefix", logging.DEBUG)
    assert mock_logger.log.call_count == 2
    mock_logger.log.assert_any_call(logging.DEBUG, f"prefix [Log chunk 1 of 2] {'A' * 30000}")
    mock_logger.log.assert_any_call(logging.DEBUG, f"prefix [Log chunk 2 of 2] {'A' * 30000}")


def test_chunk_log_output():
    output = "A" * 60000  # 60,000 characters long
    chunks = list(chunk_log_output(output, chunk_size=30000))
    assert len(chunks) == 2
    assert chunks[0] == "[Log chunk 1 of 2] " + "A" * 30000
    assert chunks[1] == "[Log chunk 2 of 2] " + "A" * 30000
