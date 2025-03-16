# interview_assistant

docker run -d \
  --name gsk_pg \
  -e POSTGRES_PASSWORD=pg123456 \
  -e POSTGRES_USER=postgre \
  -e POSTGRES_DB=gsk \
  -v pg_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15-alpine