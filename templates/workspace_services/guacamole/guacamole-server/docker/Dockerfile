FROM maven:3-jdk-11-slim AS client_build

COPY ./guacamole-auth-azure/pom.xml /pom.xml
# cache dependencies in a separate layer
RUN mvn package -Dmaven.test.skip

COPY ./guacamole-auth-azure/src /src
COPY ./docker/maven_package_and_exit_succesfully.sh /tmp/
RUN bash /tmp/maven_package_and_exit_succesfully.sh

FROM scratch AS test-results
COPY --from=client_build /target/surefire-reports/* /

FROM guacamole/guacd:1.5.5

ARG GUACAMOLE_AZURE_VERSION=0.4.1

ENV DEBIAN_FRONTEND=noninteractive

# https://github.com/microsoft/AzureTRE/issues/1937
# hadolint ignore=DL3002
USER root

RUN apk add --update --no-cache wget openssh openjdk11-jre \
    && ssh-keygen -A

ENV CATALINA_BASE=/usr/share/tomcat9/
RUN TOMCAT_ARCHIVE="tomcat.tar.gz" && \
    TOMCAT_VER="9.0.98" && \
    wget -O "$TOMCAT_ARCHIVE" -N "https://archive.apache.org/dist/tomcat/tomcat-9/v${TOMCAT_VER}/bin/apache-tomcat-${TOMCAT_VER}.tar.gz" --progress=dot:giga && \
    tar xzf "$TOMCAT_ARCHIVE" && \
    rm -f "$TOMCAT_ARCHIVE" && \
    mv "apache-tomcat-${TOMCAT_VER}/" "$CATALINA_BASE"

ENV GUACAMOLE_HOME=/guacamole/
ENV GUACAMOLE_LIB="${GUACAMOLE_HOME}/lib/"
ENV CLASSPATH=${GUACAMOLE_LIB}:${CLASSPATH}

RUN mkdir /guac-transfer

COPY ./docker/guacamole/ ${GUACAMOLE_HOME}

RUN S6_ARCHIVE=s6-overlay.tar.gz && \
    wget -O "$S6_ARCHIVE" "https://github.com/just-containers/s6-overlay/releases/download/v2.2.0.3/s6-overlay-amd64.tar.gz" --progress=dot:giga && \
    tar xzvf "$S6_ARCHIVE" -C / && \
    rm -f "$S6_ARCHIVE"

COPY ./docker/sshd_config /etc/ssh/

COPY ./docker/services /etc/services.d/

# retrieve auth integration from build image
COPY --from=client_build /target/lib/* "${GUACAMOLE_LIB}"
COPY --from=client_build "/target/guacamole-auth-tre-${GUACAMOLE_AZURE_VERSION}.jar" "${GUACAMOLE_HOME}/extensions/"

RUN wget -O "${GUACAMOLE_HOME}/guacamole.war" "http://apache.org/dyn/closer.cgi?action=download&filename=guacamole/1.5.5/binary/guacamole-1.5.5.war" --progress=dot:giga

ENV OAUTH2_PROXY_HOME=/etc/oauth2-proxy
RUN OAUTH2_PROXY_ARCHIVE=oauth2-proxy.tar.gz && \
    wget -O "$OAUTH2_PROXY_ARCHIVE" "https://github.com/oauth2-proxy/oauth2-proxy/releases/download/v7.7.1/oauth2-proxy-v7.7.1.linux-amd64.tar.gz" --progress=dot:giga && \
    mkdir -p "$OAUTH2_PROXY_HOME" && \
    tar zxpf "$OAUTH2_PROXY_ARCHIVE" -C "$OAUTH2_PROXY_HOME" --strip-components=1 && \
    rm -f "$OAUTH2_PROXY_ARCHIVE"

COPY ./docker/index.jsp "$CATALINA_BASE"/webapps/ROOT/index.jsp

RUN wget -O "/tmp/applicationinsights-agent.jar" "https://github.com/microsoft/ApplicationInsights-Java/releases/download/3.6.2/applicationinsights-agent-3.6.2.jar" --progress=dot:giga
ENV CATALINA_OPTS="$CATALINA_OPTS -javaagent:/tmp/applicationinsights-agent.jar"

ENTRYPOINT [ "/init" ]

EXPOSE 80 2222
