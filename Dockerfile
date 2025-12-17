# base image for Flask application
FROM python:3.11-slim

# set working directory
WORKDIR /app

# copy requirements and install dependencies first (leveraging Docker cache)
COPY requirements.txt .

# upgrade pip to latest version
RUN python -m pip install --upgrade pip

# install all Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the app
COPY . .

# expose the port the app will run on
EXPOSE 8000

# run the app with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app", "--workers", "3", "--threads", "2"]

