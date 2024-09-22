# FROM python:3
# WORKDIR /app
# COPY . .
# RUN pip install -r requirements.txt
# EXPOSE 5000
# ENTRYPOINT [ "python" ]
# CMD [ "app.py" ]
# #CMD [ "python", "./app.py" ]

FROM python:3.8-slim-buster
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
#CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
CMD ["python", "app.py"]
