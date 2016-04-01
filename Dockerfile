FROM hmtisr/centos:7-gosu

RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" && \
    python get-pip.py && \
    rm get-pip.py && \
    pip install watchdog

COPY watch-cmd.sh /

CMD ["bash", "/watch-cmd.sh"]
