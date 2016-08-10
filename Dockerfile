FROM python:2.7-alpine

COPY requirements.txt /
RUN pip install -r requirements.txt

RUN mkdir -p /opt/gs-sync

COPY . /opt/gs-sync/
RUN chmod +x /opt/gs-sync/*.py \
    && chmod +x /opt/gs-sync/*.sh

EXPOSE 8000

WORKDIR /opt/gs-sync
CMD ["./wrapper.sh"]
