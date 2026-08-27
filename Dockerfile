FROM public.ecr.aws/lambda/python:3.14

COPY pyproject.toml README.md ${LAMBDA_TASK_ROOT}/
COPY src ${LAMBDA_TASK_ROOT}/src

RUN python -m pip install \
    --no-cache-dir \
    --target "${LAMBDA_TASK_ROOT}" \
    "${LAMBDA_TASK_ROOT}"

CMD ["service_sentinel.app.handler"]
