# Broadsea-Methods

This is a combined image for [Achilles](https://github.com/OHDSI/Achilles) and [ETL-Synthea](https://github.com/OHDSI/ETL-Synthea).

You can review how [Achilles](#achilles) and [ETL-Synthea](#synthea-etl) are used in this project.

## Achilles

[Achilles](https://github.com/OHDSI/Achilles) is an R package used to automate the characterization of OMOP CDM data. It provides descriptive statistics and data quality checks on the OMOP CDM databases. Achilles will generally only succeed if there is data that exists in the OMOP CDM, so it is important to run this step after data has been imported.

For convenience, you may want to understand more about the [achilles.R script](#script-notes) and the [Achilles-test.R script](#achilles-testr).

### Prerequisites

In order to set up Achilles, you can work through the following steps:

## Step 1. Import Data

As a prerequisite to running Achilles, you will need to have OMOP CDM data.  You can use one of the following approaches to accomplish this step:

1. For development and test purposes, you can import data to your OMOP CDM using the [broadsea_release_pipeline](/pipelines/broadsea_release_pipeline.yaml) which includes a step to run [synthea-etl](/pipelines/README.md/#broadsea-release-pipeline).

## Step 2. Build broadsea-methods Image

1. You can build and push the broadsea-methods (which includes achilles and ETL-Synthea) image to Azure Container Registry using the [broadsea_build_pipeline](/pipelines/broadsea_build_pipeline.yaml).  You can refer to these [Pipeline Notes](/pipelines/README.md/#broadsea-build-pipeline) for more details.

### Script Notes

The following scripts will be mounted as part of the [broadsea_release_pipeline](/pipelines/broadsea_release_pipeline.yaml).

## Achilles.R

The [achilles.R script](/apps/broadsea-methods/achilles.R) will be loaded with the Docker container.  This script will connect to the OMOP CDM and perform the following steps:

1. Set database [compatibility level](https://docs.microsoft.com/en-us/sql/t-sql/statements/alter-database-transact-sql-compatibility-level?view=sql-server-ver15) to a lower level for running `achilles`

    ```sql
    ALTER DATABASE [my_sql_database_name] SET compatibility_level = 110
    ```

    > This step is included in the script as a workaround for the issue where ['the query processor ran out of internal resources and could not produce a query plan'](/docs/troubleshooting/troubleshooting_achilles_synthea.md#the-query-processor-ran-out-of-internal-resources-and-could-not-produce-a-query-plan).
    By setting the compatibility level to 110, Azure SQL will take the default compatibility level associated with SQL Server 2012, which will cause Azure SQL to use an [older query optimizer](https://docs.microsoft.com/en-us/sql/t-sql/statements/alter-database-transact-sql-compatibility-level?view=sql-server-ver15#differences-between-lower-compatibility-levels-and-level-120) to produce the query plan.  Using this setting has a tradeoff which is Azure SQL will not be able to run SQL queries which require the default compatibility level for Azure SQL.
2. Run [achilles](https://raw.githubusercontent.com/OHDSI/Achilles/master/extras/Achilles.pdf)
   > You may run into an known issue with an [arithmetic overflow error](/docs/troubleshooting/troubleshooting_achilles_synthea.md/#arithmetic-overflow-error-converting-numeric-to-data-type-varchar).  You will need to ensure you're picking up the latest changes for Achilles by [rebuilding Achilles](#step-2-build-achilles-synthea-etl-image) to pick up the [Achilles committed](https://github.com/OHDSI/Achilles/commit/e21c7e16cb4cbd653e3e572db86b536cdda86aca) fix.
3. Set database compatibility level back to the default for Azure SQL

    ```sql
    ALTER DATABASE [my_sql_database_name] SET compatibility_level = 150
    ```

    > If Azure SQL is set to a compatibility_level lower than the default you will notice issues when running queries against Azure SQL which may not be available in the lower compatibility levels as part of [Prerequisite step 1](#step-1-import-data).

This script also uses the following environment variables:

| Environment Variable Name | Description  |
|--------------|-----------|
| SQL_SERVER_NAME | Azure SQL Server Name (e.g. `my-sql-server` if you using `my-sql-server.database.windows.net`) |
| SQL_DATABASE_NAME | Azure SQL Database Name (e.g. `my-sql-server-db`) which has the CDM |
| CDM_SCHEMA | Schema for CDM (e.g. `dbo`) |
| CDM_VERSION | CDM Version (e.g. for `5.3.1` use `5.3`, see [Achilles Validation](https://github.com/OHDSI/Achilles/blob/c6b7adb6330e75c2311880db2eb3dc4c12341c4f/inst/sql/sql_server/validate_schema.sql#L501)) |
| RESULTS_SCHEMA | Schema for Results used by Achilles (e.g. `webapi`) |
| VOCAB_SCHEMA | Schema for Vocabulary (e.g. `dbo`) |
| SOURCE_NAME | CDM source name, the default is `OHDSI CDM V5 Database` |
| NUM_THREADS | Number of threads to use with Achilles, the default is `1` |

### Achilles-test.R

The [achilles-test.R script](/apps/broadsea-methods/achilles-test.R) will perform a smoke test which checks if the `achilles_results` and `achilles_analysis` tables are populated.

This script also uses the following environment variables:

| Environment Variable Name | Description  |
|--------------|-----------|
| SQL_SERVER_NAME | Azure SQL Server Name (e.g. `my-sql-server` if you using `my-sql-server.database.windows.net`) |
| SQL_DATABASE_NAME | Azure SQL Database Name (e.g. `my-sql-server-db`) which has the CDM |

## Synthea-ETL

This [directory](/apps/broadsea-methods/) contains exploratory work for generating and loading synthetic patient data via scripts found here: [https://github.com/OHDSI/ETL-Synthea](https://github.com/OHDSI/ETL-Synthea).

For convenience, you may want to learn more about the [synthea-etl.R script](#synthea-etlr-notes), the [synthea-etl-test.R script](#synthea-etl-testr-notes), and other [local development notes](#running-r-example-packages-via-dockerfile).

### Synthea-etl.R Notes

This [script](/apps/broadsea-methods/synthea-etl.R) will perform an ETL to transfer synthea generated data into your Azure SQL CDM.

This script uses the following environment variables:

| Environment Variable Name | Description  |
|--------------|-----------|
| SQL_SERVER_NAME | Azure SQL Server Name (e.g. `my-sql-server` if you using `my-sql-server.database.windows.net`) |
| SQL_DATABASE_NAME | Azure SQL Database Name (e.g. `my-sql-server-db`) which has the CDM |
| CDM_SCHEMA | Schema for CDM (e.g. `dbo`) |
| CDM_VERSION | CDM Version (e.g. for `5.3.1` use `5.3`, see [Synthea Validation](https://github.com/OHDSI/ETL-Synthea/blob/master/R/CreateVocabMapTables.r#L25)) |
| SYNTHEA_SCHEMA | Schema for Synthea (e.g. `synthea`) |
| SYNTHEA_VERSION | Synthea Version (e.g. `2.7.0`) |
| SYNTHEA_PATH | Synthea Directory for the synthea CSV data (e.g. `/home/docker/synthea_data/csv/`) |
| VOCAB_PATH | Vocabulary files path, e.g. `/home/docker/vocab_files` |

### Synthea-etl-test.R Notes

This [script](/apps/broadsea-methods/synthea-etl-test.R) is a smoke test to validate that the ETL from [Synthea](#synthea-etlr-notes) ran successfully in your Azure SQL CDM.

This script uses the following environment variables:

| Environment Variable Name | Description  |
|--------------|-----------|
| SQL_SERVER_NAME | Azure SQL Server Name (e.g. `my-sql-server` if you using `my-sql-server.database.windows.net`) |
| SQL_DATABASE_NAME | Azure SQL Database Name (e.g. `my-sql-server-db`) which has the CDM |

### Running R example packages via Dockerfile

You may find it helpful to review some of the local development notes (that have since been incorporated into the [broadsea_release_pipeline](/pipelines/README.md/#broadsea-release-pipeline) for environment release) for debugging or future development purposes:

1. How to use Synthea to [generate synthetic patient data](#use-synthea-to-generate-synthetic-patient-data)
2. How to [build and use the Docker Container with R Dependencies](#build-and-use-the-docker-container-with-r-dependencies)
3. Review other helpful [exploration notes](#exploration-notes)

#### Use Synthea to generate synthetic patient data

1. You can use Synthea to generate synthetic patient data (which is incorporated into the [broadsea_release_pipeline](/pipelines/README.md/#broadsea-release-pipeline))

    Generate Synthea files via release jar (Synthea v2.7.0)

    ```sh
    # From this /apps/broadsea-methods directory
    wget https://github.com/synthetichealth/synthea/releases/download/v2.7.0/synthea-with-dependencies.jar

    SAMPLE_SIZE=10 # Will generate 10 live patients, possibly extra dead patients as well.

    java -jar synthea-with-dependencies.jar -p $SAMPLE_SIZE -c synthea-settings.conf
    ```

    [Other generation seeds and configurations can be specified as well.](https://github.com/synthetichealth/synthea#generate-synthetic-patients)

2. You can also test the vocabulary files locally if they're unzipped and saved to `/vocab_files`

    > OPTIONAL - Download Vocabulary files from [ATHENA](https://athena.ohdsi.org/vocabulary/list)

    ```sh
    # From this /apps/broadsea-methods directory
    # Downloading default selected vocabulary from Athena and unzipped to: ./vocab_files/
    ```

    - Given that the [broadsea_release_pipeline](/pipelines/README.md/#broadsea-release-pipeline) assumes the vocabulary exists in the target Azure SQL CDM, you can utilize this approach for **local development** purposes.

#### Build and use the Docker Container with R Dependencies

1. You can use the following command to build Docker container with R dependencies

    ```sh
    # From this /apps/broadsea-methods directory
    docker build -t achilles-synthea-etl .
    ```

2. You can upload to the Azure SQL DB via R Script running in Docker Container

    ```sh
    # From this /apps/broadsea-methods directory

    export SQL_SERVER_NAME='omop-sql-server'
    export SQL_DATABASE_NAME='synthea830'

    # database schema used for connecting to the CDM.
    export CDM_SCHEMA='cdm'
    export CDM_VERSION='5.3'
    export SYNTHEA_SCHEMA='synthea'
    export SYNTHEA_VERSION='2.7.0'

    # Location of the synthea output CSV files.
    export SYNTHEA_PATH='/home/docker/synthea_data/csv/'

    # TODO: Remove when no longer needed.
    export VOCAB_PATH='/home/docker/vocab_files'
    export CREATE_CDM_SCHEMA='true'

    # Run with volume mount and env vars as parameters
    docker run -t --rm -v "$PWD":/home/docker -w /home/docker \
    -e OMOP_USER -e OMOP_PASS -e SQL_SERVER_NAME -e SQL_DATABASE_NAME \
    -e CDM_SCHEMA -e CDM_VERSION -e SYNTHEA_SCHEMA -e SYNTHEA_VERSION \
    -e SYNTHEA_PATH -e VOCAB_PATH -e CREATE_CDM_SCHEMA synthea-etl Rscript synthea-etl.R
    ```

#### Exploration Notes

- [Sql Server DatabaseConnector - prefix schema with database name.](https://forums.ohdsi.org/t/how-to-use-databaseconnector-createconnectiondetails-for-sql-server-to-connect-to-the-right-database/12725)
- [Learnings from using the Synthea data generator for use with ETL-Synthea](https://github.com/OHDSI/ETL-Synthea/issues/45)
- [Fixes required to load Synthea Tables](https://github.com/OHDSI/ETL-Synthea/commit/af15bc1f42097fb08b2291066daf399ed2b68fa1)
