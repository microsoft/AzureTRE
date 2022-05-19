# This scripts assumes that CDM schema already exists, and vocabulary is already loaded.

library(ETLSyntheaBuilder)

Sys.setenv("DATABASECONNECTOR_JAR_FOLDER" = "/home/jdbc_drivers")

# DB Configurations and Credentials
sql_server_name <- Sys.getenv("SQL_SERVER_NAME")
sql_database_name <- Sys.getenv("SQL_DATABASE_NAME")

# Schemas and other configurations
# cdm
cdm_schema <- Sys.getenv("CDM_SCHEMA")
# 5.3.1 should map to 5.3
cdm_version <- Sys.getenv("CDM_VERSION")
# synthea
synthea_schema <- Sys.getenv("SYNTHEA_SCHEMA")
# 2.7.0
synthea_version <- Sys.getenv("SYNTHEA_VERSION")


# SQL Server Schemas require database prefix
cdm_schema_full <- stringr::str_interp("${sql_database_name}.${cdm_schema}")
stringr::str_interp("cdm_schema_full = ${cdm_schema_full}")
vocab_cdm_full <- stringr::str_interp("${sql_database_name}.cdm_synthea10")
stringr::str_interp("vocab_cdm_full = ${vocab_cdm_full}")
synthea_schema_full <-  stringr::str_interp("${sql_database_name}.${synthea_schema}")
stringr::str_interp("synthea_schema_full = ${synthea_schema_full}")

# folder path for synthea CSVs
# "/home/docker/synthea_data/csv/"
synthea_directory <- Sys.getenv("SYNTHEA_PATH")
# This leverages MSI
connection_string <- stringr::str_interp("jdbc:sqlserver://${sql_server_name}.database.windows.net:1433;database=${sql_database_name};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;Authentication=ActiveDirectoryMsi;")
# To use username/password, uncomment below:
# connection_string <- stringr::str_interp("jdbc:sqlserver://${sql_server_name}.database.windows.net:1433;database=${sql_database_name};user=${omop_user};password=${omop_pass};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;")
cd <- createConnectionDetails(dbms = "sql server", connectionString=connection_string)

# TODO - refine - continue on warning.
try_catch_bloc <- function(x){
    tryCatch(
        expr = {
            message(x)
            message("Successfully executed the call.")
        },
        error = function(e){
            message('Caught an error!')
            print(e)
        },
        warning = function(w){
            message('Caught an warning!')
            print(w)
        },
        finally = {
            message('All done, quitting.')
        }
    )
}

# drop and recreate Synthea schema and tables
print ("Dropping Synthea tables")
try_catch_bloc(ETLSyntheaBuilder::DropSyntheaTables(cd,synthea_schema_full))

conn <- DatabaseConnector::connect(cd)

print ("Dropping Synthea schema if it exists")
DatabaseConnector::executeSql(conn, stringr::str_interp("DROP SCHEMA IF EXISTS ${synthea_schema}"))

print ("Creating Synthea schema if does not exist")
DatabaseConnector::executeSql(conn, stringr::str_interp("IF NOT EXISTS (SELECT 0
               FROM information_schema.schemata
               WHERE schema_name='${synthea_schema}')
BEGIN
  EXEC sp_executesql N'CREATE SCHEMA ${synthea_schema}';
END"))

print ("Creating Synthea tables")
try_catch_bloc(ETLSyntheaBuilder::CreateSyntheaTables(connectionDetails = cd, syntheaSchema = synthea_schema_full, syntheaVersion = synthea_version))


# Load Synthea tables under a schema specific to Synthea
print ("Loading Synthea tables")
try_catch_bloc(ETLSyntheaBuilder::LoadSyntheaTables(connectionDetails = cd, syntheaSchema = synthea_schema_full, syntheaFileLoc = synthea_directory))


# Synthea ETL - Transform data under Synthea schema to CDM format in the CDM schema
print ("Performing Synthea ETL")
try_catch_bloc(ETLSyntheaBuilder::LoadEventTables(connectionDetails = cd, cdmSchema = cdm_schema_full, syntheaSchema = synthea_schema_full, cdmVersion = cdm_version, syntheaVersion = synthea_version))
