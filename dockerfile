FROM python:3.13
WORKDIR /anton_n_feedback_bot
RUN apt update -y && apt install -y gettext-base && apt clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /anton_n_feedback_bot/
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY ./ /anton_n_feedback_bot/
COPY ./.env /anton_n_feedback_bot/.env
CMD ["python3", "main.py"]