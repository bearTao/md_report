-- 创建微网格相关表（MySQL版本）

-- 1. 微网格概况表
DROP TABLE IF EXISTS microgrid.micro_grid_overview_w;
CREATE TABLE microgrid.micro_grid_overview_w (
    starttime timestamp NULL COMMENT '开始时间',
    endtime timestamp NULL COMMENT '结束时间',
    wgid varchar(128) NULL COMMENT '微网格ID',
    micro_grid_name varchar(128) NULL COMMENT '微网格中文名',
    micro_grid_enname varchar(128) NULL COMMENT '微网格英文名',
    city varchar(128) NULL COMMENT '城市',
    area_administration varchar(128) NULL COMMENT '行政区',
    area varchar(128) NULL COMMENT '区县',
    area_m varchar(128) NULL COMMENT '面积(m2)',
    cover_scene varchar(128) NULL COMMENT '覆盖场景',
    userstoresident varchar(128) NULL COMMENT '常驻用户数',
    usersto4g varchar(128) NULL COMMENT '4G用户数',
    usersto5g varchar(128) NULL COMMENT '5G用户数',
    equipment_company varchar(128) NULL COMMENT '设备厂家',
    cell_count BIGINT NULL DEFAULT 0 COMMENT '涉及小区数',
    cell_4g_count BIGINT NULL DEFAULT 0 COMMENT '涉及4G小区数',
    cell_5g_count BIGINT NULL DEFAULT 0 COMMENT '涉及5G小区数',
    complaint_count BIGINT NULL DEFAULT 0 COMMENT '涉及聚类投诉数',
    complaint_grid_count BIGINT NULL DEFAULT 0 COMMENT '涉及重投栅格数',
    wgid_score DECIMAL(28, 6) NULL COMMENT '网格得分',
    wgid_deduction TEXT NULL COMMENT '主要失分项',
    problem_cluster_count INT NULL DEFAULT 0 COMMENT '覆盖融合问题点数',
    problem_count BIGINT NULL DEFAULT 0 COMMENT '覆盖问题数',
    problem_build_dj_count BIGINT NULL DEFAULT 0 COMMENT '低小聚类-楼宇问题数',
    problem_build_gj_count BIGINT NULL DEFAULT 0 COMMENT '高大聚类-楼宇问题数',
    problem_build_d_count BIGINT NULL DEFAULT 0 COMMENT '高大单点-楼宇问题数',
    problem_bad_other_count BIGINT NULL DEFAULT 0 COMMENT '质差劣于竞对-楼宇问题数',
    problem_grid_4g_count BIGINT NULL DEFAULT 0 COMMENT '栅格聚类-4G栅格MDT问题数',
    problem_grid_5g_count BIGINT NULL DEFAULT 0 COMMENT '栅格聚类-5G栅格云瞰问题数',
    problem_cloud_4g_count BIGINT NULL DEFAULT 0 COMMENT '栅格聚类-云瞰4G弱覆盖且劣于竞对栅格数',
    problem_cloud_5g_count BIGINT NULL DEFAULT 0 COMMENT '栅格聚类-云瞰5G弱覆盖且劣于竞对栅格数',
    plan_count BIGINT NULL DEFAULT 0 COMMENT '有效工程站点数',
    plan_indoor_count BIGINT NULL DEFAULT 0 COMMENT '有效工程站点数（室分）',
    plan_outdoor_count BIGINT NULL DEFAULT 0 COMMENT '有效工程站点数（宏站/微小站）',
    plan_problem_count BIGINT NULL DEFAULT 0 COMMENT '与弱覆盖区域强关联工程站点数',
    gr_problem_count BIGINT NULL DEFAULT 0 COMMENT '干扰问题数',
    jg_problem_count BIGINT NULL DEFAULT 0 COMMENT '结构问题数',
    rl_problem_count BIGINT NULL DEFAULT 0 COMMENT '容量问题数',
    xn_problem_count BIGINT NULL DEFAULT 0 COMMENT '性能问题数',
    wh_problem_count BIGINT NULL DEFAULT 0 COMMENT '维护问题数',
    key_scenes_count BIGINT NULL DEFAULT 0 COMMENT '涉及督办重要场景数',
    key_scenes_list TEXT NULL COMMENT '涉及督办重要场景清单',
    report_id varchar(255) NULL COMMENT '预分析报告文件ID',
    longitude DECIMAL(28, 6) NULL COMMENT '经度',
    latitude DECIMAL(28, 6) NULL COMMENT '纬度'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微网格概况表';

-- 2. 微网格指标评分表
DROP TABLE IF EXISTS microgrid.micro_grid_index_score_w;
CREATE TABLE microgrid.micro_grid_index_score_w (
    starttime timestamp NULL COMMENT '开始时间',
    endtime timestamp NULL COMMENT '结束时间',
    wgid varchar(128) NULL COMMENT '微网格ID',
    `index` varchar(128) NULL COMMENT '指标名称',
    `values` DECIMAL(28, 6) NULL COMMENT '指标值',
    index_weight DECIMAL(28, 6) NULL COMMENT '指标权重',
    index_score DECIMAL(28, 6) NULL COMMENT '指标得分',
    index_deduction DECIMAL(28, 6) NULL COMMENT '指标失分'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微网格指标评分表';

-- 3. 微网格工程规划站点表
DROP TABLE IF EXISTS microgrid.micro_grid_plan_w;
CREATE TABLE microgrid.micro_grid_plan_w (
    starttime timestamp NULL COMMENT '开始时间',
    endtime timestamp NULL COMMENT '结束时间',
    wgid varchar(128) NULL COMMENT '微网格ID',
    site_name varchar(255) NULL COMMENT '站点名称',
    site_type varchar(64) NULL COMMENT '站点类型',
    longitude DECIMAL(28, 6) NULL COMMENT '经度',
    latitude DECIMAL(28, 6) NULL COMMENT '纬度',
    plan_status varchar(64) NULL COMMENT '规划状态',
    is_related_problem BOOLEAN NULL DEFAULT FALSE COMMENT '是否关联问题'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微网格工程规划站点表';

-- 4. 微网格问题聚类表
DROP TABLE IF EXISTS microgrid.micro_grid_problem_cluster_m;
CREATE TABLE microgrid.micro_grid_problem_cluster_m (
    starttime timestamp NULL COMMENT '开始时间',
    endtime timestamp NULL COMMENT '结束时间',
    wgid varchar(128) NULL COMMENT '微网格ID',
    cluster_id varchar(128) NULL COMMENT '聚类ID',
    cluster_type varchar(128) NULL COMMENT '聚类类型',
    cluster_count INT NULL DEFAULT 0 COMMENT '聚类数量',
    flong DECIMAL(28, 6) NULL COMMENT '经度',
    flat DECIMAL(28, 6) NULL COMMENT '纬度'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微网格问题聚类表';

-- 5. 微网格栅格云瞰问题表
DROP TABLE IF EXISTS microgrid.micro_grid_problem_grid_cloud_m;
CREATE TABLE microgrid.micro_grid_problem_grid_cloud_m (
    starttime timestamp NULL COMMENT '开始时间',
    endtime timestamp NULL COMMENT '结束时间',
    wgid varchar(128) NULL COMMENT '微网格ID',
    gridid BIGINT NULL COMMENT '栅格ID',
    flong DECIMAL(28, 6) NULL COMMENT '经度',
    flat DECIMAL(28, 6) NULL COMMENT '纬度',
    intsampling_count INT NULL DEFAULT 0 COMMENT '采样点数',
    intweakcover_count INT NULL DEFAULT 0 COMMENT '弱覆盖点数',
    fweakcoverrate DECIMAL(28, 6) NULL COMMENT '弱覆盖率'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微网格栅格云瞰问题表';

-- 6. 微网格问题楼宇聚类表
DROP TABLE IF EXISTS microgrid.micro_grid_problem_build_cluster_m;
CREATE TABLE microgrid.micro_grid_problem_build_cluster_m (
    starttime timestamp NULL COMMENT '开始时间',
    endtime timestamp NULL COMMENT '结束时间',
    wgid varchar(128) NULL COMMENT '微网格ID',
    bldg_cluster_id varchar(128) NULL COMMENT '楼宇聚类ID',
    bldg_cluster_type varchar(128) NULL COMMENT '楼宇聚类类型',
    bldg_cluster_count INT NULL DEFAULT 0 COMMENT '楼宇聚类数量',
    bldg_cluster_list TEXT NULL COMMENT '楼宇ID列表'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微网格问题楼宇聚类表';

