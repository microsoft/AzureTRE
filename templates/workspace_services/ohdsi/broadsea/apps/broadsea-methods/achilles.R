# See ./README.md for more details
# Load Achilles library - Should already be installed in whatever container is running this.
library("Achilles")

# Setup Environment Variables
Sys.setenv("DATABASECONNECTOR_JAR_FOLDER" = "/home/jdbc_drivers")

sql_server_name <- Sys.getenv("SQL_SERVER_NAME")
sql_database_name <- Sys.getenv("SQL_DATABASE_NAME")
cdm_schema <- Sys.getenv("CDM_SCHEMA")
# note that the CDM Version should be simplified e.g. instead of 5.3.1, use 5.3
# see https://github.com/OHDSI/Achilles/blob/c6b7adb6330e75c2311880db2eb3dc4c12341c4f/inst/sql/sql_server/validate_schema.sql#L501 for details
cdm_version <- Sys.getenv("CDM_VERSION")
results_schema <- Sys.getenv("RESULTS_SCHEMA")
vocab_schema <- Sys.getenv("VOCAB_SCHEMA")
source_name <- Sys.getenv("SOURCE_NAME")
num_threads <- Sys.getenv("NUM_THREADS")

ACHILLES_SQL_SERVER_COMPATIBILITY_LEVEL <- 110
DEFAULT_AZURE_SQL_SERVER_COMPATIBILITY_LEVEL <- 150

# Setup SQL Connection
connectionString <- stringr::str_interp("jdbc:sqlserver://${sql_server_name}.database.windows.net:1433;database=${sql_database_name};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;Authentication=ActiveDirectoryMsi;")
connectionDetails <- createConnectionDetails(dbms = "sql server", connectionString = connectionString)
conn <- DatabaseConnector::connect(connectionDetails)

database_name <- DatabaseConnector::querySql(conn, stringr::str_interp("SELECT DB_NAME()"))
print(database_name)

db_name <- toString(database_name)

result <- tryCatch({
    # Set compatibility level for Achilles 
    # https://docs.microsoft.com/en-us/sql/t-sql/statements/alter-database-transact-sql-compatibility-level?view=sql-server-ver15
    # We are lowering the compatibility level for Azure SQL to be able to create the query plan
    # Achilles generates a complex query for analysis so changing the compatibility level will help Azure SQL produce the query plan
    print ("Set compatibility level for Achilles")
    query <- stringr::str_interp("ALTER DATABASE [${db_name}] SET compatibility_level = ${ACHILLES_SQL_SERVER_COMPATIBILITY_LEVEL};")
    DatabaseConnector::executeSql(conn, query)

    # call achilles
    achilles(connectionDetails = connectionDetails,
            cdmDatabaseSchema = stringr::str_interp("${sql_database_name}.${cdm_schema}"),
            resultsDatabaseSchema = stringr::str_interp("${sql_database_name}.${results_schema}"),
            vocabDatabaseSchema = stringr::str_interp("${sql_database_name}.${vocab_schema}"),
            sourceName = source_name,
            cdmVersion = cdm_version,
            numThreads = num_threads,
            outputFolder = "output")
}, warning = function(warning_condition) {
    message(warning_condition)
}, error = function(error_condition) {
    message(error_condition)
}, finally={
    # Restore default compatibility level for Azure SQL
    # Note that if you don't reset the compabitibility level 
    # you will notice issues with other components such as running queries which rely on the default compatibility level may not work
    print ("Restore default compatibility level for Azure SQL")
    query <- stringr::str_interp("ALTER DATABASE [${db_name}] SET compatibility_level = ${DEFAULT_AZURE_SQL_SERVER_COMPATIBILITY_LEVEL};")
    DatabaseConnector::executeSql(conn, query)
})






