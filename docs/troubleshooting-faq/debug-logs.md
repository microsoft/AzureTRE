# Setting the logging level to DEBUG on the Resource Processor and API

For security, the API and Resource PRocessor are configured to not show detailed error messages and stack trace when an error occurs.

You can enable debugging on the API and Resource Processor by setting `logging_level=debug` under developer_settings section in your`config.yaml` file.

Once set, you need to run `make deploy-core` to update the settings on the API and Resource Processor. You should start to see logs with severity level `0` appear in the Application Insights logs.
