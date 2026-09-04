# CRM — Vận Tải Đường Bộ

Hệ thống quản lý công ty, bắt đầu bằng module **CRM (khách hàng/bán hàng)**. Kiến trúc API-first (Django REST Framework) để sau này app điện thoại dùng chung một API với web, không phải viết lại.

- `backend/` — Django + DRF, PostgreSQL
- `frontend/` — React (Vite), gọi API qua JWT
- `infra/` — cấu hình nginx, script sao lưu tự động 3 nơi
- `.github/workflows/deploy.yml` — tự động deploy khi push nhánh `main`

## Chạy thử ở máy local

**Backend** (cần Python 3.12+):
```bash
cd backend
python -m venv venv
venv/Scripts/activate   # Windows | source venv/bin/activate trên Mac/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_groups        # tạo 2 nhóm quyền: Quản lý / Nhân viên kinh doanh
python manage.py createsuperuser
python manage.py runserver 8001
```
Không cần cài Postgres để chạy thử — nếu không có biến `POSTGRES_DB`, backend tự dùng SQLite.

**Frontend** (cần Node.js):
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8001" > .env.local
npm run dev
```
Mở `http://localhost:5173`, đăng nhập bằng tài khoản superuser vừa tạo.

## Triển khai lên VPS thật (sản xuất)

Dùng Docker Compose (`docker-compose.yml` ở gốc repo) chạy 3 dịch vụ: `db` (Postgres), `backend` (Django/gunicorn), `nginx`.

1. Tạo VPS (khuyến nghị DigitalOcean, Ubuntu, cài sẵn Docker)
2. Clone repo này vào VPS, tạo file `backend/.env` từ `backend/.env.example`, điền mật khẩu Postgres thật
3. `docker compose up -d --build`
4. Trong Cloudflare: thêm DNS record `crm.vantaiduongbo.net` (CNAME hoặc A) trỏ vào IP VPS, bật Proxy (mây cam)
5. Để mỗi lần push code lên `main` tự động deploy: vào GitHub repo → Settings → Secrets and variables → Actions, thêm 4 secret:
   - `SSH_HOST` — IP của VPS
   - `SSH_USER` — user SSH (vd. `root`)
   - `SSH_KEY` — private key SSH để đăng nhập vào VPS
   - `DEPLOY_PATH` — đường dẫn tới thư mục repo trên VPS (vd. `/root/crm`)

## Sao lưu dữ liệu (bắt buộc — tự động 3 nơi)

`infra/backup.sh` mỗi lần chạy: dump database → nén → giữ lại trên VPS (nơi 1) → đẩy lên Cloudflare R2 (nơi 2) → đẩy lên Backblaze B2 (nơi 3).

Cần chuẩn bị 1 lần trên VPS:
1. Cài `rclone`, tạo 2 bucket "crm-backups" trên **Cloudflare R2** và **Backblaze B2** (2 nhà cung cấp khác nhau — để không mất cả 2 bản sao cùng lúc nếu 1 bên gặp sự cố)
2. Điền key thật vào `infra/rclone.conf.example` rồi lưu thành `~/.config/rclone/rclone.conf`
3. Thêm vào crontab để chạy mỗi đêm:
   ```
   0 2 * * * /root/crm/infra/backup.sh >> /root/crm/infra/backups/cron.log 2>&1
   ```

## Vai trò & phân quyền

- **Quản lý**: thấy và sửa toàn bộ khách hàng, đơn hàng
- **Nhân viên kinh doanh**: chỉ thấy khách hàng do mình phụ trách (`assigned_to`)

Gán vai trò cho user qua Django admin (`/admin/`) → Users → chọn user → thêm vào nhóm "Quản lý" hoặc "Nhân viên kinh doanh".
