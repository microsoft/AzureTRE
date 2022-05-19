# hadolint ignore=DL3006
FROM rocker/tidyverse

# hadolint ignore=DL3008,DL3009,DL3015
RUN apt-get update && apt-get install -y python-dev openjdk-8-jdk liblzma-dev libbz2-dev \
&& R CMD javareconf

## Install Rserve
RUN install2.r \
	Rserve \
	RSclient \
	openssl \
	httr \
	xml2 \
	remotes \
&& rm -rf /tmp/download_packages/ /tmp/*.rds

## TODO - Download and unzip jdbc drivers and delete after COPY step.
# https://docs.microsoft.com/en-us/sql/connect/jdbc/download-microsoft-jdbc-driver-for-sql-server?view=sql-server-ver15

## Copy JDBC Drivers
COPY jdbc_drivers /home/jdbc_drivers

## Install OHDSI R packages
RUN installGithub.r \
	OHDSI/Achilles \
	OHDSI/ETL-Synthea \
&& rm -rf /tmp/downloaded_packages/ /tmp/*.rds

CMD ["Rscript"]
