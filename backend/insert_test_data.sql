-- 插入测试数据 for ZQGY0174

-- 1. 微网格概况数据
INSERT INTO microgrid.micro_grid_overview_w (
    starttime, endtime, wgid, micro_grid_name, city, area, area_m, cover_scene,
    userstoresident, usersto4g, usersto5g, equipment_company,
    cell_count, cell_4g_count, cell_5g_count, wgid_score,
    problem_count, problem_build_dj_count, problem_build_d_count, problem_bad_other_count,
    problem_grid_4g_count, problem_grid_5g_count,
    plan_count, plan_indoor_count, plan_outdoor_count, plan_problem_count,
    gr_problem_count, jg_problem_count, wh_problem_count,
    longitude, latitude
) VALUES (
    '2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '测试微网格-174',
    '上海', '浦东新区', '2500000', '住宅区',
    '8500', '6200', '5800', '华为',
    45, 28, 17, 82.5,
    156, 45, 32, 28,
    25, 26,
    18, 8, 10, 12,
    15, 8, 6,
    121.5234, 31.2304
);

-- 2. 指标评分数据
INSERT INTO microgrid.micro_grid_index_score_w (starttime, endtime, wgid, `index`, `values`, index_weight, index_score, index_deduction)
VALUES 
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '覆盖质量', 85.5, 30.0, 25.65, 4.35),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '用户感知', 88.2, 25.0, 22.05, 2.95),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '网络性能', 90.1, 20.0, 18.02, 1.98),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '资源利用', 75.8, 15.0, 11.37, 3.63),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '工程进度', 80.0, 10.0, 8.00, 2.00);

-- 3. 工程规划站点数据
INSERT INTO microgrid.micro_grid_plan_w (starttime, endtime, wgid, site_name, site_type, longitude, latitude, plan_status, is_related_problem)
VALUES
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '浦东新区-站点001', '室分', 121.5240, 31.2310, '规划中', TRUE),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '浦东新区-站点002', '宏站', 121.5250, 31.2320, '施工中', TRUE),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '浦东新区-站点003', '微站', 121.5260, 31.2330, '已完成', FALSE),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '浦东新区-站点004', '室分', 121.5270, 31.2340, '规划中', TRUE),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', '浦东新区-站点005', '宏站', 121.5280, 31.2350, '待审批', FALSE);

-- 4. 问题聚类数据
INSERT INTO microgrid.micro_grid_problem_cluster_m (starttime, endtime, wgid, cluster_id, cluster_type, cluster_count, flong, flat)
VALUES
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 'CLS001', '弱覆盖聚类', 15, 121.5235, 31.2305),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 'CLS002', '弱覆盖聚类', 12, 121.5245, 31.2315),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 'CLS003', '质差聚类', 8, 121.5255, 31.2325);

-- 5. 栅格MDT问题数据
INSERT INTO microgrid.micro_grid_problem_grid_mdt_m (starttime, endtime, wgid, gridid, flong, flat, intmdt_count, intweak_count)
VALUES
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 1001, 121.5236, 31.2306, 500, 85),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 1002, 121.5246, 31.2316, 450, 72),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 1003, 121.5256, 31.2326, 520, 91);

-- 6. 栅格云瞰问题数据
INSERT INTO microgrid.micro_grid_problem_grid_cloud_m (starttime, endtime, wgid, gridid, flong, flat, intsampling_count, intweakcover_count, fweakcoverrate)
VALUES
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 2001, 121.5237, 31.2307, 600, 95, 0.158),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 2002, 121.5247, 31.2317, 580, 88, 0.152),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 2003, 121.5257, 31.2327, 610, 102, 0.167);

-- 7. 问题楼宇聚类数据
INSERT INTO microgrid.micro_grid_problem_build_cluster_m (starttime, endtime, wgid, bldg_cluster_id, bldg_cluster_type, bldg_cluster_count, bldg_cluster_list)
VALUES
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 'BC001', '低小聚类', 8, 'BLDG001,BLDG002,BLDG003,BLDG004,BLDG005,BLDG006,BLDG007,BLDG008'),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 'BC002', '高大聚类', 5, 'BLDG009,BLDG010,BLDG011,BLDG012,BLDG013'),
('2025-01-01 00:00:00', '2025-03-31 23:59:59', 'ZQGY0174', 'BC003', '劣于竞对', 6, 'BLDG014,BLDG015,BLDG016,BLDG017,BLDG018,BLDG019');

-- 8. 问题楼宇明细（插入一些示例数据）
INSERT INTO microgrid.micro_grid_problem_build_m (
    starttime, endtime, wgid, bldg_id, bldg_name, longitude, latitude, height_m, area_m,
    fourg_cm_mr_count, fourg_cm_ssbfrsrp_dbm, fourg_cm_dlsinr_db, fourg_cm_weak_cov_mr_ratio, fourg_cm_poor_qual_mr_ratio,
    fiveg_cm_mr_count, fiveg_cm_ssbfrsrp_dbm, fiveg_cm_ssbfdlsinr_db, fiveg_cm_weak_cov_mr_ratio_ssb, fiveg_cm_poor_qual_mr_ratio_ssb,
    is_bad_cov_4g, is_bad_qual_4g, is_bad_other_4g, is_bad_cov_5g, is_bad_qual_5g, is_bad_other_5g,
    build_type, is_issue_build, is_bad_build, is_bad_other_build, is_bad_build_5g
) VALUES
('2025-01-01', '2025-03-31', 'ZQGY0174', 'BLDG001', '测试楼宇A', 121.5238, 31.2308, 45.5, 8500, 1200, -105.5, 8.2, 15.5, 8.3, 980, -108.2, 10.5, 12.8, 6.5, TRUE, FALSE, FALSE, TRUE, FALSE, FALSE, '住宅楼', TRUE, TRUE, FALSE, FALSE),
('2025-01-01', '2025-03-31', 'ZQGY0174', 'BLDG002', '测试楼宇B', 121.5248, 31.2318, 52.0, 9200, 1350, -112.8, 5.5, 22.3, 12.5, 1100, -115.5, 7.8, 18.5, 10.2, TRUE, TRUE, FALSE, TRUE, TRUE, FALSE, '写字楼', TRUE, TRUE, FALSE, TRUE),
('2025-01-01', '2025-03-31', 'ZQGY0174', 'BLDG014', '竞对劣势楼宇', 121.5258, 31.2328, 38.0, 7200, 1050, -108.5, 6.8, 18.2, 9.5, 850, -111.2, 8.5, 15.5, 8.8, FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, '商业楼', TRUE, FALSE, TRUE, FALSE);

