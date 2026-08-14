# Triển khai lên AWS — hướng dẫn deploy demo

> **Đọc mục Chi phí trước khi làm bất cứ điều gì.** Template này khởi tạo một EC2
> instance có GPU, **tính phí theo giờ ngay cả khi không ai gọi API**.

Mức đầu tư: **demo/nộp đồ án**, không phải production. Một instance, không load
balancer, không auto-scaling, không managed DB. Xem [ADR-0001](../adr/0001-local-llm-first.md)
để hiểu vì sao Ollama local là lựa chọn mặc định — deploy này **giữ nguyên** lựa
chọn đó (chạy Ollama trên chính EC2 GPU) thay vì chuyển sang API cloud trả phí theo
token.

---

## 0. Chi phí (đọc trước)

| Thành phần | Chi phí |
| --- | --- |
| EC2 `g4dn.xlarge` (1× T4 16GB) | **~$0.526/giờ** ở `us-east-1` — tương đương **~$380/tháng nếu chạy 24/7** |
| EBS gp3 100GB | ~$8/tháng |
| Data transfer out | Không đáng kể ở quy mô demo |

**Cách giữ chi phí thấp:**
- **Dừng instance khi không demo** (`aws ec2 stop-instances`). EBS vẫn tính phí nhỏ khi dừng, nhưng EC2 compute (phần đắt nhất) thì không.
- **Xoá stack hoàn toàn sau khi nộp bài** (§ 5) — đây là bước quan trọng nhất để không bị tính phí ngoài ý muốn.
- Không có cơ chế auto-shutdown trong template này (cố tình giữ đơn giản cho demo). Nếu quên tắt, instance chạy vô thời hạn và bị tính phí liên tục.

---

## 1. Điều kiện tiên quyết

```bash
aws configure          # hoặc aws sso login — cần Access Key hoặc SSO đã login
aws sts get-caller-identity   # xác nhận đã đăng nhập đúng account
```

**Kiểm tra quota GPU trước khi launch** — tài khoản AWS mới thường có quota **0**
cho instance G/VT:

```bash
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-DB2E81BA \
  --region us-east-1
```

Nếu `Value` là `0`, xin tăng quota tại **Service Quotas → Amazon EC2 → Running
On-Demand G and VT instances** (thường duyệt trong vài giờ, đôi khi vài ngày —
làm bước này sớm).

Cần một **VPC có public subnet** (VPC mặc định của tài khoản là đủ):

```bash
aws ec2 describe-vpcs --filters Name=is-default,Values=true \
  --query 'Vpcs[0].VpcId' --output text
aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc-id-vừa-lấy> \
  --query 'Subnets[0].SubnetId' --output text
```

(Tuỳ chọn) Tạo key pair nếu muốn SSH bằng khoá thay vì SSM Session Manager:

```bash
aws ec2 create-key-pair --key-name iae-demo --query 'KeyMaterial' --output text > iae-demo.pem
chmod 400 iae-demo.pem
```

---

## 2. Khởi tạo hạ tầng (CloudFormation)

```bash
aws cloudformation create-stack \
  --stack-name iae-demo \
  --template-body file://deploy/aws/cloudformation.yaml \
  --capabilities CAPABILITY_IAM \
  --parameters \
      ParameterKey=VpcId,ParameterValue=<vpc-id> \
      ParameterKey=SubnetId,ParameterValue=<subnet-id> \
      ParameterKey=KeyPairName,ParameterValue=iae-demo \
      ParameterKey=SSHLocation,ParameterValue=$(curl -s https://checkip.amazonaws.com)/32
```

Không muốn quản lý key pair? Bỏ hai dòng `KeyPairName`/`SSHLocation` — truy cập qua
SSM Session Manager (xem § 4).

Theo dõi tiến trình (~3–5 phút để instance chạy, cộng thêm **~2–3 phút** để
user-data cài Ollama và tải model `qwen3.5:4b`):

```bash
aws cloudformation wait stack-create-complete --stack-name iae-demo
aws cloudformation describe-stacks --stack-name iae-demo --query 'Stacks[0].Outputs'
```

Lấy `PublicIp` từ output — cần cho bước deploy code tiếp theo.

**Kiểm tra user-data đã xong** trước khi deploy app (tránh deploy vào máy chưa có Ollama):

```bash
aws ssm start-session --target <InstanceId-từ-output>
# trong phiên SSM:
cat /var/log/iae-userdata-done   # có file này nghĩa là đã xong
tail -50 /var/log/iae-userdata.log   # xem log nếu chưa xong hoặc lỗi
```

---

## 3. Deploy code ứng dụng (GitHub Actions)

Hạ tầng (§ 2) và code ứng dụng (bước này) **tách riêng có chủ đích**: hạ tầng chạy
một lần, hiếm khi đổi; code deploy mỗi lần push. Workflow `deploy.yml` **chỉ trigger
thủ công** (`workflow_dispatch`) — không tự động chạy khi push lên `main`, vì mỗi
lần deploy chạm vào một máy đang tính phí thật.

### 3.1 Cấu hình GitHub Secrets

Vào **Settings → Secrets and variables → Actions**, tạo:

| Secret | Giá trị |
| --- | --- |
| `EC2_HOST` | `PublicIp` từ output CloudFormation |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Nội dung file `.pem` (toàn bộ, kể cả `-----BEGIN...-----`) |

> Nếu không tạo key pair ở § 1, tạo key pair mới chỉ cho việc deploy và thêm public
> key vào `~/.ssh/authorized_keys` của instance qua SSM Session Manager, thay vì mở
> lại CloudFormation.

### 3.2 Chạy deploy

**Actions → Deploy to AWS → Run workflow**, gõ `deploy` vào ô confirm. Workflow sẽ:
chạy test → rsync code lên `/opt/iae` → `docker compose -f docker-compose.prod.yml up -d --build` → chờ `/health` trả `ok:true`.

### 3.3 Kiểm tra

```bash
curl http://<PublicIp>:8000/health
curl http://<PublicIp>:8000/exams
curl -X POST http://<PublicIp>:8000/evaluate/T2-002
# hoặc mở trực tiếp: http://<PublicIp>:8000/docs
```

Lần gọi `/evaluate` đầu tiên sau khi container mới khởi động vẫn nhanh, vì
`OLLAMA_KEEP_ALIVE=-1` được set trong user-data — model được giữ nóng trong VRAM
vĩnh viễn, không phải chờ cold load 110s như mô tả trong
[tech-spec.md § 5.1](../02-technical/tech-spec.md).

---

## 4. Truy cập instance để debug

**Không cần key pair** (khuyến nghị — IAM role đã gắn sẵn `AmazonSSMManagedInstanceCore`):

```bash
aws ssm start-session --target <InstanceId>
```

**Có key pair:**

```bash
ssh -i iae-demo.pem ubuntu@<PublicIp>
```

Trong máy: `docker compose -f /opt/iae/docker-compose.prod.yml logs -f app`,
`ollama ps`, `journalctl -u ollama -f`.

---

## 5. Dọn dẹp (bắt buộc sau khi nộp bài / demo xong)

```bash
aws cloudformation delete-stack --stack-name iae-demo
aws cloudformation wait stack-delete-complete --stack-name iae-demo
```

Xoá toàn bộ: EC2 instance, security group, IAM role. EBS volume có
`DeleteOnTermination: true` nên cũng bị xoá theo, không để lại chi phí lưu trữ mồ côi.

**Xác nhận đã xoá sạch** (tránh trường hợp stack delete thất bại một phần):

```bash
aws ec2 describe-instances --filters "Name=tag:Project,Values=IELTS-AI-Evaluator" \
  --query 'Reservations[].Instances[].{Id:InstanceId,State:State.Name}'
```

Nếu còn instance ở trạng thái khác `terminated`, xoá thủ công:
`aws ec2 terminate-instances --instance-ids <id>`.

---

## 6. Những gì cố tình KHÔNG làm ở bản demo này

| Không có | Vì sao chấp nhận được cho demo | Cần gì nếu lên production |
| --- | --- | --- |
| HTTPS/TLS | Nộp đồ án không cần | ALB + ACM certificate |
| Auto-scaling | 1 instance đủ cho demo | ASG + nhiều AZ |
| Managed DB | P0 chưa có DB (xem [roadmap P1.7](../04-roadmap/roadmap.md)) | RDS PostgreSQL |
| Auto-shutdown khi rảnh | Giữ template đơn giản | Lambda + EventBridge tắt ngoài giờ |
| Secrets Manager | Không có secret nhạy cảm (không API key) | Cần nếu thêm cloud LLM provider |
| CloudWatch alarms/logging tập trung | Debug qua SSM đủ cho demo | CloudWatch Agent + dashboard |

Đây là các hạng mục có thể bổ sung sau nếu dự án cần chạy thật, không phải thiếu sót
của bản deploy này.
