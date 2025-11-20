## 表结构与索引

* 在 `test_db` 中执行以下 SQL，创建两张测试表和常用索引：

```
-- 可选：显式指定 schema（如非 public 请自行替换）
CREATE SCHEMA IF NOT EXISTS public;

-- 能耗/功率明细
CREATE TABLE IF NOT EXISTS public.meter_readings (
  ts TIMESTAMP NOT NULL,
  device_id TEXT NOT NULL,
  energy_kwh NUMERIC,
  power_kw NUMERIC
);
CREATE INDEX IF NOT EXISTS idx_meter_readings_ts ON public.meter_readings(ts);
CREATE INDEX IF NOT EXISTS idx_meter_readings_device ON public.meter_readings(device_id);

-- 告警明细
CREATE TABLE IF NOT EXISTS public.alarms (
  ts TIMESTAMP NOT NULL,
  device_id TEXT NOT NULL,
  level TEXT NOT NULL,
  message TEXT
);
CREATE INDEX IF NOT EXISTS idx_alarms_ts ON public.alarms(ts);
CREATE INDEX IF NOT EXISTS idx_alarms_device ON public.alarms(device_id);
CREATE INDEX IF NOT EXISTS idx_alarms_level ON public.alarms(level);
```

## 清空旧数据

```
TRUNCATE public.meter_readings;
TRUNCATE public.alarms;
```

## 灌入样例数据（最近14天）

* 使用 `generate_series` 和 `random()` 生成可重复结构的数据；能耗/功率在白天（9-20点）按较高基线、夜间按较低基线，并叠加噪声。

```
-- 生成 14 天 × 24 小时 × 5 台设备 的小时级数据
WITH hours AS (
  SELECT (date_trunc('hour', now()) - interval '14 days') + (gs * interval '1 hour') AS ts
  FROM generate_series(0, 14*24-1) AS gs
), devices AS (
  SELECT 'DEV-'||LPAD(i::text,2,'0') AS device_id
  FROM generate_series(1,5) i
)
INSERT INTO public.meter_readings(ts, device_id, energy_kwh, power_kw)
SELECT h.ts, d.device_id,
       round(GREATEST(5.0,
             (CASE WHEN EXTRACT(HOUR FROM h.ts) BETWEEN 9 AND 20 THEN 20 ELSE 10 END)
             + (random()*6 - 3)) * 1.0, 3) AS energy_kwh,
       round(GREATEST(5.0,
             (CASE WHEN EXTRACT(HOUR FROM h.ts) BETWEEN 9 AND 20 THEN 20 ELSE 10 END)
             + (random()*6 - 3)), 3) AS power_kw
FROM hours h CROSS JOIN devices d;
```

```
-- 生成约 300 条随机告警（覆盖 14 天、设备、等级、消息）
INSERT INTO public.alarms(ts, device_id, level, message)
SELECT
  (now() - interval '14 days') + (random() * interval '14 days') AS ts,
  'DEV-'||LPAD(CAST(ceil(random()*5) AS text),2,'0') AS device_id,
  CASE WHEN random() < 0.1 THEN 'ERROR'
       WHEN random() < 0.4 THEN 'WARN'
       ELSE 'INFO' END AS level,
  (ARRAY['过载','欠压','通讯中断','温度过高','电流异常'])[ceil(random()*5)] AS message
FROM generate_series(1, 300);
```

## 验证与示例查询

```
-- 计数校验（应为 14*24*5=1680 行）
SELECT count(*) AS meter_rows FROM public.meter_readings;
SELECT count(*) AS alarm_rows FROM public.alarms;

-- 与模板一致的示例范围（按需替换日期）
SELECT sum(energy_kwh) AS total_kwh
FROM public.meter_readings
WHERE ts >= '2025-11-10' AND ts < '2025-11-17';

SELECT avg(power_kw) AS avg_kw
FROM public.meter_readings
WHERE ts >= '2025-11-10' AND ts < '2025-11-17';

SELECT device_id, count(*) AS cnt
FROM public.alarms
WHERE ts >= '2025-11-10' AND ts < '2025-11-17'
GROUP BY device_id
ORDER BY cnt DESC
LIMIT 5;
```

## 说明

* 表名与字段严格对齐当前模板与后端查询：`meter_readings(ts, device_id, energy_kwh, power_kw)` 与 `alarms(ts, device_id, level, message)`。

* 如你的库非 `public` schema，请将所有 `public.` 前缀替换为实际 schema；或在连接中默认 schema 设置为 `public`。

* 完成上述 SQL 后，直接触发报告生成即可；我会随即重跑 A/B 模板并继续演示 Agent 修改流程。

