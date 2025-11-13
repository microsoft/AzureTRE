FROM maven:3.9-eclipse-temurin-17-alpine AS client_build

COPY ./guacamole-auth-azure/pom.xml /pom.xml
# cache dependencies in a separate layer
RUN mvn package -Dmaven.test.skip

COPY ./guacamole-auth-azure/src /src
COPY ./docker/maven_package_and_exit_succesfully.sh /tmp/
RUN bash /tmp/maven_package_and_exit_succesfully.sh

FROM scratch AS test-results
COPY --from=client_build /target/surefire-reports/* /

FROM guacamole/guacd:1.6.0

ARG GUACAMOLE_AZURE_VERSION=0.5.0

ENV DEBIAN_FRONTEND=noninteractive

# https://github.com/microsoft/AzureTRE/issues/1937
# hadolint ignore=DL3002
USER root

RUN apk add --update --no-cache wget openjdk17-jre tini bash

RUN addgroup -S guac \
    && adduser -S -G guac -h /home/guacsvc guacsvc

ENV CATALINA_BASE=/usr/share/tomcat9/
ENV GUACAMOLE_HOME=/guacamole/
ENV GUACAMOLE_LIB="${GUACAMOLE_HOME}/lib/"
ENV CLASSPATH=${GUACAMOLE_LIB}
ENV OAUTH2_PROXY_HOME=/etc/oauth2-proxy

RUN mkdir -p "$GUACAMOLE_HOME" "$GUACAMOLE_LIB" /guac-transfer "$OAUTH2_PROXY_HOME"

RUN TOMCAT_ARCHIVE="tomcat.tar.gz" && \
    TOMCAT_VER="9.0.111" && \
    wget -O "$TOMCAT_ARCHIVE" -N "https://archive.apache.org/dist/tomcat/tomcat-9/v${TOMCAT_VER}/bin/apache-tomcat-${TOMCAT_VER}.tar.gz" --progress=dot:giga && \
    tar xzf "$TOMCAT_ARCHIVE" && \
    rm -f "$TOMCAT_ARCHIVE" && \
    mv "apache-tomcat-${TOMCAT_VER}/" "$CATALINA_BASE"

RUN sed -i "s#port=\"8080\"#port=\"8080\" maxHttpHeaderSize=\"262144\"#" "$CATALINA_BASE/conf/server.xml" && \
    sed -i "s#unpackWARs=\"true\" autoDeploy=\"true\">#><Context path=\"guacamole\" docBase=\"${GUACAMOLE_HOME}guacamole.war\"/>#" "$CATALINA_BASE/conf/server.xml"

RUN wget -O "${GUACAMOLE_HOME}/guacamole.war" "http://apache.org/dyn/closer.cgi?action=download&filename=guacamole/1.6.0/binary/guacamole-1.6.0.war" --progress=dot:giga

RUN OAUTH2_PROXY_ARCHIVE=oauth2-proxy.tar.gz && \
    wget -O "$OAUTH2_PROXY_ARCHIVE" "https://github.com/oauth2-proxy/oauth2-proxy/releases/download/v7.13.0/oauth2-proxy-v7.13.0.linux-amd64.tar.gz" --progress=dot:giga && \
    tar zxpf "$OAUTH2_PROXY_ARCHIVE" -C "$OAUTH2_PROXY_HOME" --strip-components=1 && \
    rm -f "$OAUTH2_PROXY_ARCHIVE"

RUN wget -O "/tmp/applicationinsights-agent.jar" "https://github.com/microsoft/ApplicationInsights-Java/releases/download/3.6.2/applicationinsights-agent-3.6.2.jar" --progress=dot:giga

COPY ./docker/guacamole/ ${GUACAMOLE_HOME}
COPY ./docker/start-guacamole.sh /usr/local/bin/start-guacamole.sh

# retrieve auth integration from build image
COPY --from=client_build /target/lib/* "${GUACAMOLE_LIB}"
COPY --from=client_build "/target/guacamole-auth-tre-${GUACAMOLE_AZURE_VERSION}.jar" "${GUACAMOLE_HOME}/extensions/"

COPY ./docker/index.jsp "$CATALINA_BASE"/webapps/ROOT/index.jsp

RUN chmod +x /usr/local/bin/start-guacamole.sh && \
    chown -R guacsvc:guac "$GUACAMOLE_HOME" "$GUACAMOLE_LIB" /usr/share/tomcat9 /guac-transfer "$OAUTH2_PROXY_HOME" /tmp/applicationinsights-agent.jar

ENTRYPOINT [ "/sbin/tini", "--", "/usr/local/bin/start-guacamole.sh" ]

EXPOSE 80

USER guacsvc
