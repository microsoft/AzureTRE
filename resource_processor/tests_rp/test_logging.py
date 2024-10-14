import pytest
from mock import patch
import logging
from shared.logging import shell_output_logger

pytestmark = pytest.mark.asyncio


@patch("shared.logging.logger")
async def test_shell_output_logger_empty_console_output(mock_logger):
    shell_output_logger("", "prefix", logging.DEBUG)
    mock_logger.debug.assert_called_once_with("shell console output is empty.")


@patch("shared.logging.logger")
async def test_shell_output_logger_image_not_present_locally(mock_logger):
    console_output = "Unable to find image 'test_image' locally\nexecution completed successfully!"
    shell_output_logger(console_output, "prefix", logging.DEBUG)
    mock_logger.debug.assert_called_with("Image not present locally, removing text from console output.")
    mock_logger.log.assert_called_with(logging.INFO, "prefix execution completed successfully!")


@patch("shared.logging.logger")
async def test_shell_output_logger_execution_completed_successfully(mock_logger):
    console_output = "execution completed successfully!"
    shell_output_logger(console_output, "prefix", logging.DEBUG)
    mock_logger.log.assert_called_with(logging.INFO, "prefix execution completed successfully!")


@patch("shared.logging.logger")
async def test_shell_output_logger_normal_case(mock_logger):
    console_output = "Some logs"
    shell_output_logger(console_output, "prefix", logging.DEBUG)
    mock_logger.log.assert_called_with(logging.DEBUG, "prefix Some logs")
