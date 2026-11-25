ARG GITEA_TAG=1.15
ARG CERTIFICATE_URL=https://www.digicert.com/CACerts/BaltimoreCyberTrustRoot.crt.pem

FROM gitea/gitea:${GITEA_TAG}
# need to pass args to stage
ARG CERTIFICATE_URL
RUN wget -nv -O /usr/local/share/ca-certificates/mysql.crt.pem ${CERTIFICATE_URL} && update-ca-certificates
COPY configure_gitea_admin.sh /
# The script hides the secrets in the Gitea output, which goes to the console log.
ENTRYPOINT ["/bin/bash", "-c", "bash /configure_gitea_admin.sh & /usr/bin/entrypoint"]
