ARG GITEA_TAG=1.17.3
ARG CERTIFICATE_URL=https://www.digicert.com/CACerts/BaltimoreCyberTrustRoot.crt.pem

FROM gitea/gitea:${GITEA_TAG}
# need to pass args to stage
ARG CERTIFICATE_URL
RUN wget -q -O /usr/local/share/ca-certificates/mysql.crt.pem ${CERTIFICATE_URL} && update-ca-certificates
COPY . /

RUN /usr/sbin/adduser -D -g users gitea

ENTRYPOINT ["/bin/bash", "-c",  "./configure_gitea.sh & /usr/bin/entrypoint"]
