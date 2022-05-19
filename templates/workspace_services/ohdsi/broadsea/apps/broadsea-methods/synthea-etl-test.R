library(ETLSyntheaBuilder)

Sys.setenv("DATABASECONNECTOR_JAR_FOLDER" = "/home/jdbc_drivers")

# DB Configurations and Credentials
sql_server_name <- Sys.getenv("SQL_SERVER_NAME")
sql_database_name <- Sys.getenv("SQL_DATABASE_NAME")

# This leverages MSI
connection_string <- stringr::str_interp("jdbc:sqlserver://${sql_server_name}.database.windows.net:1433;database=${sql_database_name};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;Authentication=ActiveDirectoryMsi;")

# To use username/password, uncomment below:
cd <- createConnectionDetails(dbms = "sql server", connectionString=connection_string)
conn <- DatabaseConnector::connect(cd)

print ("Querying data from Synthea tables")
DatabaseConnector::querySql(conn, stringr::str_interp("SELECT TOP 10 * FROM synthea.patients"))

syntheaTableCount <- DatabaseConnector::querySql(conn, stringr::str_interp("SELECT COUNT(*) FROM synthea.patients"))

# Make sure table count is larger than 0
stopifnot (syntheaTableCount > 0)
