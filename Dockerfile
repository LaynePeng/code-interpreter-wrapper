# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY codeinterpreter-wrapper.py .
COPY external-codeinterpreter.json .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV PORT=8000

# Run codeinterpreter-wrapper.py when the container launches
CMD ["python", "codeinterpreter-wrapper.py"]
