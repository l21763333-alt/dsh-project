#!/usr/bin/env bash
# 初始化 MySQL 数据库与专用账号（供本地 MySQL / docker compose 起的 mysql 使用）
# 用法：MYSQL_ROOT_PASSWORD=你的root密码 ./scripts/init_db.sh
set -e

DB_NAME="${MYSQL_DB:-recruit_ai}"
DB_USER="${MYSQL_USER:-recruit}"
DB_PASS="${MYSQL_PASSWORD:-recruit123}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"

echo "[init_db] 连接 ${MYSQL_HOST}:${MYSQL_PORT} 初始化数据库 ${DB_NAME} ..."
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u root -p"${MYSQL_ROOT_PASSWORD:-}" <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
SQL
echo "[init_db] 完成：数据库 $DB_NAME / 账号 $DB_USER"
