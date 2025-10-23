# 网络访问配置 - IP地址支持

## 配置日期
2025-10-22

## 问题描述
前端和后端服务默认只监听 `localhost (127.0.0.1)`，无法通过本机IP地址 `10.10.20.10` 访问，导致局域网其他设备无法连接。

## 解决方案

### 1. 前端配置（Vite开发服务器）

#### 修改文件：`frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // ✅ 监听所有网络接口
    port: 5173,
    strictPort: false,
  }
})
```

**变更说明**：
- 添加 `server.host: '0.0.0.0'`，允许通过任何网络接口访问
- 明确指定端口 `5173`
- `strictPort: false` 允许端口被占用时自动切换

#### 修改文件：`frontend/src/api/client.ts`

```typescript
const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://10.10.20.10:8000',  // ✅ 默认使用IP
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

**变更说明**：
- 将默认后端地址从 `localhost:8000` 改为 `10.10.20.10:8000`
- 仍支持通过环境变量 `VITE_API_BASE_URL` 覆盖

#### 新增文件：`frontend/.env.development`

```env
# 开发环境配置
# API 基础 URL - 使用本机 IP，允许局域网访问
VITE_API_BASE_URL=http://10.10.20.10:8000
```

**说明**：
- Vite 会自动加载 `.env.development` 文件
- 开发模式下优先使用此配置

---

### 2. 后端配置（FastAPI + Uvicorn）

#### 文件：`backend/app/main.py`

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # ✅ 已配置
```

**状态**：
- ✅ 后端已经配置了 `host="0.0.0.0"`
- ✅ 无需修改

---

## 访问方式

配置完成后，可以通过以下方式访问：

### 前端访问
- ✅ `http://localhost:5173` - 本地访问
- ✅ `http://127.0.0.1:5173` - 本地回环
- ✅ `http://10.10.20.10:5173` - 通过本机IP访问 ⭐
- ✅ `http://<局域网IP>:5173` - 从局域网其他设备访问

### 后端访问
- ✅ `http://localhost:8000` - 本地访问
- ✅ `http://127.0.0.1:8000` - 本地回环
- ✅ `http://10.10.20.10:8000` - 通过本机IP访问 ⭐
- ✅ `http://<局域网IP>:8000` - 从局域网其他设备访问

---

## 启动服务

### 前端启动

```bash
cd frontend
npm run dev
```

启动后会显示：
```
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://10.10.20.10:5173/
```

### 后端启动

```bash
cd backend
# 方式1：直接运行
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 方式2：使用脚本
python app/main.py
```

---

## 测试验证

### 1. 验证前端访问

```bash
# 从本机访问
curl http://10.10.20.10:5173

# 从其他机器访问（替换<other-ip>为你的机器IP）
curl http://10.10.20.10:5173
```

### 2. 验证后端访问

```bash
# 测试健康检查接口
curl http://10.10.20.10:8000/health

# 预期返回
{"status":"healthy"}
```

### 3. 验证前后端联调

在浏览器中访问：
```
http://10.10.20.10:5173/templates
```

检查：
- ✅ 页面能正常加载
- ✅ 能获取模板列表（说明前端成功调用后端API）
- ✅ 网络请求指向 `http://10.10.20.10:8000`

---

## 安全注意事项

### ⚠️ 开发环境
- 配置 `host: '0.0.0.0'` 会将服务暴露给局域网
- **仅在受信任的网络环境使用**
- 不要在公网环境直接暴露开发服务器

### ✅ 生产环境
- 前端：使用 `npm run build` 构建后部署到 Nginx/Apache
- 后端：使用 Gunicorn + Nginx 部署，配置防火墙和反向代理
- 启用 HTTPS
- 配置 CORS 白名单

---

## 故障排查

### 问题1：仍然无法通过IP访问

**检查防火墙**：
```bash
# Linux
sudo ufw status
sudo ufw allow 5173
sudo ufw allow 8000

# Windows
# 在"Windows 防火墙高级安全"中添加入站规则
```

**检查端口占用**：
```bash
# Linux/Mac
lsof -i :5173
lsof -i :8000

# Windows
netstat -ano | findstr :5173
netstat -ano | findstr :8000
```

### 问题2：跨域错误（CORS）

**后端已配置CORS**：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题3：环境变量未生效

**解决方案**：
```bash
# 删除缓存，重启开发服务器
cd frontend
rm -rf node_modules/.vite
npm run dev
```

---

## 相关文件清单

### 已修改文件
- ✅ `frontend/vite.config.ts` - 添加 server 配置
- ✅ `frontend/src/api/client.ts` - 修改默认 baseURL
- ✅ `backend/app/main.py` - 已配置（无需修改）

### 新增文件
- ✅ `frontend/.env.development` - 开发环境配置

### 配置参考
- `frontend/README.md` - 环境变量说明
- `backend/app/main.py` - Uvicorn 启动配置

---

## 下一步建议

### 可选优化

1. **配置代理**（可选）
   
   在 `vite.config.ts` 中添加代理，简化API调用：
   ```typescript
   server: {
     host: '0.0.0.0',
     port: 5173,
     proxy: {
       '/api': {
         target: 'http://10.10.20.10:8000',
         changeOrigin: true,
       }
     }
   }
   ```

2. **生产环境配置**
   
   创建 `frontend/.env.production`：
   ```env
   VITE_API_BASE_URL=https://your-domain.com/api
   ```

3. **Docker部署**
   
   创建 `docker-compose.yml` 统一管理前后端服务。

---

**配置完成** ✅

现在可以通过 `http://10.10.20.10:5173` 访问前端，
通过 `http://10.10.20.10:8000` 访问后端！

