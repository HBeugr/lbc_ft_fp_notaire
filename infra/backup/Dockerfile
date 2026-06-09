FROM mysql:8.0

RUN microdnf install -y cronie && microdnf clean all

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

RUN echo '0 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1' | crontab -

CMD ["crond", "-n"]
