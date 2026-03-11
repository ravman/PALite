FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY . .
RUN cd backend && python3 seed.py
EXPOSE 3001
CMD ["python3", "backend/app.py"]
