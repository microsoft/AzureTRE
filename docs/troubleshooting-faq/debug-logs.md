# Setting the logging level to DEBUG on the Resource Processor and API

For security, the API and Resource PRocessor are configured to not show detailed error messages and stack trace when an error occurs.

You can enable debugging on the API and Resource Processor by setting `logging_level=debug` under developer_settings section in your`config.yaml` file.

To enable debugging on an already running instance of the API:

1. Go to App Service for the API and select **Settings > Configuration**.
1. Click the configuration with name **LOGGING_LEVEL** and set the **Value** to **DEBUG**.
