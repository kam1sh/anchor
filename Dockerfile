FROM python:3.7-alpine
RUN apk update && apk add uwsgi uwsgi-http uwsgi-python3

COPY config /app/config/
WORKDIR /app

COPY dist/*.whl /tmp/
RUN pip3 install /tmp/*.whl && rm /tmp/*.whl

USER uwsgi

CMD [ \
    "uwsgi", "--master", "--need-app", \
    "--plugins", "python3", \
    "--http11-socket", "0.0.0.0:8080", \
    "--pythonpath", "/usr/local/lib/python3.7/site-packages/", \
    "--module", "config.wsgi:application" \
]
# uwsgi --plugins python3 --master --need-app --http11-socket 0.0.0.0:8080 --pythonpath /usr/local/lib/python3.7/site-packages/ --module "anchor.wsgi:app"

