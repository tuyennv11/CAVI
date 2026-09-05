#!/usr/bin/env bash
# Sao lưu database ra 3 nơi độc lập: (1) đĩa VPS, (2) Cloudflare R2, (3) Backblaze B2.
# Chạy hằng ngày qua cron trên VPS, từ thư mục gốc dự án (nơi có docker-compose.yml).
#
# Cần chuẩn bị trước (một lần):
#   - `rclone config` đã tạo 2 remote tên "r2" và "b2" (xem infra/rclone.conf.example)
#   - biến POSTGRES_DB/POSTGRES_USER lấy từ backend/.env
set -euo pipefail

cd "$(dirname "$0")/.."
set -a; source backend/.env; set +a

BACKUP_DIR="infra/backups"
STAMP=$(date +%Y-%m-%d_%H%M)
FILE="crm_${STAMP}.sql.gz"
LOG="$BACKUP_DIR/backup.log"

mkdir -p "$BACKUP_DIR"

echo "[$STAMP] Bắt đầu sao lưu..." | tee -a "$LOG"

# 1) Dump từ container Postgres, nén, lưu tại chỗ (nơi 1)
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_DIR/$FILE"
echo "[$STAMP] Đã tạo $BACKUP_DIR/$FILE ($(du -h "$BACKUP_DIR/$FILE" | cut -f1)) — nơi 1 (đĩa VPS)" | tee -a "$LOG"

# 2) Đẩy lên Cloudflare R2 — nơi 2
# --s3-no-check-bucket: API token chỉ có quyền Object Read & Write trên riêng bucket này,
# không có quyền kiểm tra/tạo bucket — cờ này báo rclone bỏ qua bước đó.
if rclone copy "$BACKUP_DIR/$FILE" r2:crm-backups/ --s3-no-check-bucket 2>>"$LOG"; then
  echo "[$STAMP] Đã đẩy lên R2 — nơi 2: OK" | tee -a "$LOG"
else
  echo "[$STAMP] ĐẨY LÊN R2 THẤT BẠI — kiểm tra $LOG" | tee -a "$LOG"
fi

# 3) Đẩy lên Backblaze B2 — nơi 3 (nhà cung cấp độc lập, tránh cùng lúc mất cả 2 nếu 1 bên sự cố)
if rclone copy "$BACKUP_DIR/$FILE" b2:CAVITUYEN/ 2>>"$LOG"; then
  echo "[$STAMP] Đã đẩy lên B2 — nơi 3: OK" | tee -a "$LOG"
else
  echo "[$STAMP] ĐẨY LÊN B2 THẤT BẠI — kiểm tra $LOG" | tee -a "$LOG"
fi

# Chỉ giữ 7 bản gần nhất trên đĩa VPS (R2/B2 giữ lâu hơn, không xoá ở đây)
ls -1t "$BACKUP_DIR"/crm_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm --
echo "[$STAMP] Hoàn tất." | tee -a "$LOG"
