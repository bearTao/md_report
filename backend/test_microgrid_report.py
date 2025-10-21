wgid:
  type: string
  source: user_input
  required: true
  ui_config:
    input_type: text
    placeholder: 请输入微网格ID，例如：JYRC1951
  description: 微网格标识（用户输入）
overview:
  type: object
  schema:
    type: object
    properties:
      area:
        type: string
      city:
        type: string
      wgid:
        type: string
      area_m:
        type: string
      endtime:
        type: string
      latitude:
        type: number
      longitude:
        type: number
      starttime:
        type: string
      usersto4g:
        type: string
      usersto5g:
        type: string
      cell_count:
        type: number
      plan_count:
        type: number
      wgid_score:
        type: number
      cover_scene:
        type: string
      cell_4g_count:
        type: number
      cell_5g_count:
        type: number
      problem_count:
        type: number
      micro_grid_name:
        type: string
      userstoresident:
        type: string
      gr_problem_count:
        type: number
      jg_problem_count:
        type: number
      wh_problem_count:
        type: number
      equipment_company:
        type: string
      plan_indoor_count:
        type: number
      plan_outdoor_count:
        type: number
      plan_problem_count:
        type: number
      problem_build_d_count:
        type: number
      problem_grid_4g_count:
        type: number
      problem_grid_5g_count:
        type: number
      problem_build_dj_count:
        type: number
      problem_bad_other_count:
        type: number
  source: sql
  required: true
  sql_config:
    query: |
      SELECT 
        starttime,
        endtime,
        wgid,
        micro_grid_name,
        city,
        area,
        area_m,
        cover_scene,
        userstoresident,
        usersto4g,
        usersto5g,
        equipment_company,
        cell_count,
        cell_4g_count,
        cell_5g_count,
        wgid_score,
        problem_count,
        problem_build_dj_count,
        problem_build_d_count,
        problem_bad_other_count,
        problem_grid_4g_count,
        problem_grid_5g_count,
        plan_count,
        plan_indoor_count,
        plan_outdoor_count,
        plan_problem_count,
        gr_problem_count,
        jg_problem_count,
        wh_problem_count,
        longitude,
        latitude
      FROM microgrid.micro_grid_overview_w
      WHERE wgid = :wgid
      ORDER BY endtime DESC
      LIMIT 1
    timeout: 10
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: first_row
  description: 微网格概况信息
  dependencies:
    - wgid
plan_sites:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        latitude:
          type: number
        longitude:
          type: number
        site_name:
          type: string
        site_type:
          type: string
        plan_status:
          type: string
        is_related_problem:
          type: boolean
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        site_name,
        site_type,
        longitude,
        latitude,
        plan_status,
        is_related_problem
      FROM microgrid.micro_grid_plan_w
      WHERE wgid = :wgid
      ORDER BY 
        CASE WHEN is_related_problem THEN 1 ELSE 2 END,
        site_name
    timeout: 10
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 工程规划站点列表
  dependencies:
    - wgid
index_scores:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        index:
          type: string
        values:
          type: number
        index_score:
          type: number
        index_weight:
          type: number
        index_deduction:
          type: number
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        "index",
        "values",
        index_weight,
        index_score,
        index_deduction
      FROM microgrid.micro_grid_index_score_w
      WHERE wgid = :wgid
      ORDER BY "index"
    timeout: 10
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 指标评分列表
  dependencies:
    - wgid
report_metadata:
  type: object
  schema:
    type: object
    properties:
      version:
        type: string
      report_id:
        type: string
      generated_date:
        type: string
  source: system
  required: true
  description: 报告元数据
  system_config:
    fields:
      version:
        value: 1.0.0
      report_id:
        generator: uuid
      generated_date:
        format: '%Y年%m月%d日'
        generator: datetime
problem_clusters:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        flat:
          type: number
        flong:
          type: number
        cluster_id:
          type: string
        cluster_type:
          type: string
        cluster_count:
          type: number
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        cluster_id,
        cluster_type,
        cluster_count,
        flong,
        flat
      FROM microgrid.micro_grid_problem_cluster_m
      WHERE wgid = :wgid
      ORDER BY cluster_count DESC
    timeout: 10
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 覆盖融合问题点列表
  dependencies:
    - wgid
problem_grid_mdt:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        flat:
          type: number
        flong:
          type: number
        gridid:
          type: number
        intmdt_count:
          type: number
        intweak_count:
          type: number
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        gridid,
        flong,
        flat,
        intmdt_count,
        intweak_count
      FROM microgrid.micro_grid_problem_grid_mdt_m
      WHERE wgid = :wgid
        AND intweak_count > 0
      ORDER BY intweak_count DESC
      LIMIT 100
    timeout: 15
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 栅格MDT问题列表
  dependencies:
    - wgid
problem_buildings:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        area_m:
          type: number
        bldg_id:
          type: string
        height_m:
          type: number
        latitude:
          type: number
        bldg_name:
          type: string
        longitude:
          type: number
        build_type:
          type: string
        is_bad_build:
          type: boolean
        is_bad_cov_4g:
          type: boolean
        is_bad_cov_5g:
          type: boolean
        is_bad_qual_4g:
          type: boolean
        is_bad_qual_5g:
          type: boolean
        is_issue_build:
          type: boolean
        is_bad_build_5g:
          type: boolean
        is_bad_other_4g:
          type: boolean
        is_bad_other_5g:
          type: boolean
        fiveg_cm_mr_count:
          type: number
        fourg_cm_mr_count:
          type: number
        fourg_cm_dlsinr_db:
          type: number
        is_bad_other_build:
          type: boolean
        fiveg_cm_ssbfrsrp_dbm:
          type: number
        fourg_cm_ssbfrsrp_dbm:
          type: number
        fiveg_cm_ssbfdlsinr_db:
          type: number
        fourg_cm_weak_cov_mr_ratio:
          type: number
        fourg_cm_poor_qual_mr_ratio:
          type: number
        fiveg_cm_weak_cov_mr_ratio_ssb:
          type: number
        fiveg_cm_poor_qual_mr_ratio_ssb:
          type: number
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        bldg_id,
        bldg_name,
        longitude,
        latitude,
        height_m,
        area_m,
        fourg_cm_mr_count,
        fourg_cm_ssbfrsrp_dbm,
        fourg_cm_dlsinr_db,
        fourg_cm_weak_cov_mr_ratio,
        fourg_cm_poor_qual_mr_ratio,
        fiveg_cm_mr_count,
        fiveg_cm_ssbfrsrp_dbm,
        fiveg_cm_ssbfdlsinr_db,
        fiveg_cm_weak_cov_mr_ratio_ssb,
        fiveg_cm_poor_qual_mr_ratio_ssb,
        is_bad_cov_4g,
        is_bad_qual_4g,
        is_bad_other_4g,
        is_bad_cov_5g,
        is_bad_qual_5g,
        is_bad_other_5g,
        build_type,
        is_issue_build,
        is_bad_build,
        is_bad_other_build,
        is_bad_build_5g
      FROM microgrid.micro_grid_problem_build_m
      WHERE wgid = :wgid
        AND is_issue_build = true
      ORDER BY 
        CASE WHEN is_bad_other_build THEN 1 ELSE 2 END,
        bldg_name
    timeout: 15
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 问题楼宇列表
  dependencies:
    - wgid
problem_grid_cloud:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        flat:
          type: number
        flong:
          type: number
        gridid:
          type: number
        fweakcoverrate:
          type: number
        intsampling_count:
          type: number
        intweakcover_count:
          type: number
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        gridid,
        flong,
        flat,
        intsampling_count,
        intweakcover_count,
        fweakcoverrate
      FROM microgrid.micro_grid_problem_grid_cloud_m
      WHERE wgid = :wgid
        AND intweakcover_count > 0
      ORDER BY intweakcover_count DESC
      LIMIT 100
    timeout: 15
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 栅格云瞰问题列表
  dependencies:
    - wgid
building_type_stats:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        count:
          type: number
        build_type:
          type: string
        percentage:
          type: number
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        build_type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
      FROM microgrid.micro_grid_problem_build_m
      WHERE wgid = :wgid
        AND is_issue_build = true
      GROUP BY build_type
      ORDER BY count DESC
    timeout: 5
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 楼宇类型分布统计
  dependencies:
    - wgid
grid_mdt_weak_samples:
  type: number
  source: sql
  default: 0
  required: false
  sql_config:
    query: |
      SELECT COALESCE(SUM(intweak_count), 0) as total
      FROM microgrid.micro_grid_problem_grid_mdt_m
      WHERE wgid = :wgid
    timeout: 5
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: first_value
  description: 栅格MDT弱覆盖采样点数
  dependencies:
    - wgid
report_generated_time:
  type: string
  source: system
  required: true
  description: 报告生成时间
  system_config:
    fields:
      timestamp:
        format: '%Y-%m-%d %H:%M:%S'
        generator: datetime
grid_mdt_total_samples:
  type: number
  source: sql
  default: 0
  required: false
  sql_config:
    query: |
      SELECT COALESCE(SUM(intmdt_count), 0) as total
      FROM microgrid.micro_grid_problem_grid_mdt_m
      WHERE wgid = :wgid
    timeout: 5
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: first_value
  description: 栅格MDT总采样点数
  dependencies:
    - wgid
buildings_4g_weak_count:
  type: number
  source: sql
  default: 0
  required: false
  sql_config:
    query: |
      SELECT COUNT(*) as count
      FROM microgrid.micro_grid_problem_build_m
      WHERE wgid = :wgid
        AND is_bad_cov_4g = true
    timeout: 5
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: first_value
  description: 4G弱覆盖楼宇数量
  dependencies:
    - wgid
buildings_5g_weak_count:
  type: number
  source: sql
  default: 0
  required: false
  sql_config:
    query: |
      SELECT COUNT(*) as count
      FROM microgrid.micro_grid_problem_build_m
      WHERE wgid = :wgid
        AND is_bad_cov_5g = true
    timeout: 5
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: first_value
  description: 5G弱覆盖楼宇数量
  dependencies:
    - wgid
problem_building_clusters:
  type: array
  schema:
    type: array
    items:
      type: object
      properties:
        bldg_cluster_id:
          type: string
        bldg_cluster_list:
          type: string
        bldg_cluster_type:
          type: string
        bldg_cluster_count:
          type: number
  source: sql
  default: []
  required: false
  sql_config:
    query: |
      SELECT 
        bldg_cluster_id,
        bldg_cluster_type,
        bldg_cluster_count,
        bldg_cluster_list
      FROM microgrid.micro_grid_problem_build_cluster_m
      WHERE wgid = :wgid
      ORDER BY bldg_cluster_count DESC
    timeout: 10
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: all_rows
  description: 问题楼宇聚类信息
  dependencies:
    - wgid
buildings_worse_competitor_count:
  type: number
  source: sql
  default: 0
  required: false
  sql_config:
    query: |
      SELECT COUNT(*) as count
      FROM microgrid.micro_grid_problem_build_m
      WHERE wgid = :wgid
        AND is_bad_other_build = true
    timeout: 5
    connection: microgrid_db
    parameters:
      - wgid
    result_mode: first_value
  description: 劣于竞对楼宇数量
  dependencies:
    - wgid
