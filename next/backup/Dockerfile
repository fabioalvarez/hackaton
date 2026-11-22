# Backup watcher: a shell script with jq. It is the only service that writes to the data volume.
FROM alpine:3.20

RUN apk add --no-cache jq

COPY watch.sh /usr/local/bin/watch.sh

CMD ["sh", "/usr/local/bin/watch.sh"]
