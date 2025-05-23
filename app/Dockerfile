# Dockerfile
FROM python:3.11.7-slim


# 更新 pip 并配置镜像源
RUN pip config set global.extra-index-url "https://mirrors.cernet.edu.cn/pypi/web/simple"
RUN pip install --upgrade pip setuptools wheel

# 安装系统依赖
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# 安装netcat用于等待数据库启动
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制整个应用目录
COPY . .

# 创建静态文件目录
RUN mkdir -p /app/static

# 复制静态文件
COPY static/ /app/static/

# 添加启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]