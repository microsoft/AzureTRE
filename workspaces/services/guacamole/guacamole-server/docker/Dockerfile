# FROM maven:3-jdk-11-openj9 AS client_build

# COPY ./guacamole-auth-azure/pom.xml pom.xml 

# COPY ./guacamole-auth-azure/src src

# RUN mvn package

FROM guacamole/guacd:1.3.0

# ARG GUACAMOLE_AZURE_VERSION=0.1

ENV DEBIAN_FRONTEND=noninteractive

USER root

# dependencies

RUN apt-get update && apt-get install wget curl openssh-server apt-transport-https gnupg -y && \
    apt-get autoclean && apt-get autoremove && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/AdoptOpenJDK/openjdk11-binaries/releases/download/jdk-11.0.11%2B9/OpenJDK11U-jre_x64_linux_hotspot_11.0.11_9.tar.gz && \
    mkdir -p /usr/lib/jvm/java-11-openjdk-amd64/ && \
    tar xzf OpenJDK11U-jre_x64_linux_hotspot_11.0.11_9.tar.gz -C /usr/lib/jvm/java-11-openjdk-amd64/ --strip-components=1 && \
    export PATH=/usr/lib/jvm/java-11-openjdk-amd64/bin:$PATH && java -version

RUN \
    TOMCAT_VER=`curl --silent http://mirror.vorboss.net/apache/tomcat/tomcat-9/ | grep v9 -m 1 | awk '{split($5,c,">v") ; split(c[2],d,"/") ; print d[1]}'` && \
    wget -N http://mirror.vorboss.net/apache/tomcat/tomcat-9/v${TOMCAT_VER}/bin/apache-tomcat-${TOMCAT_VER}.tar.gz &&\
    tar xzf apache-tomcat-${TOMCAT_VER}.tar.gz && \
    rm -f apache-tomcat-${TOMCAT_VER}.tar.gz && \
    mv apache-tomcat-${TOMCAT_VER}/ /usr/share/tomcat9/

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# retrieve auth integration from build image
# COPY --from=client_build /target/guacamole-azure-${GUACAMOLE_AZURE_VERSION}.jar /guacamole/extensions/

ENV CATALINA_BASE=/usr/share/tomcat9/

ENV GUACAMOLE_HOME=/guacamole/

RUN mkdir ${GUACAMOLE_HOME}

RUN wget -O ${GUACAMOLE_HOME}/guacamole.war 'http://apache.org/dyn/closer.cgi?action=download&filename=guacamole/1.3.0/binary/guacamole-1.3.0.war'  

RUN mkdir /guac-transfer

COPY ./docker/guacamole/ ${GUACAMOLE_HOME}

RUN wget -O s6-overlay.tar.gz https://github.com/just-containers/s6-overlay/releases/download/v2.2.0.3/s6-overlay-amd64.tar.gz && tar xzvf s6-overlay.tar.gz -C /

COPY ./docker/sshd_config /etc/ssh/

COPY ./docker/services /etc/services.d/

ENTRYPOINT [ "/init" ]

EXPOSE 80 2222