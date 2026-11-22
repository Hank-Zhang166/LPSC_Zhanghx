# 样品与可见证据
字段以独立实体为行，父子 ID 永不复用。可空观测需同时记录 missing_reason。新行或版本记录改动，不覆盖原始结果。
| 对象 | 主键 / 外键 | 观测 / 元数据 |
|---|---|---|
| 粉体 | powder_id, candidate_id, process_block, confirmation_lock_id | nominal_x, measured_composition, phase_evidence_id, parent_lot, sop_version |
| 压片 | pellet_id, powder_id | condition_id, relative_density, thickness_cm, area_cm2, geometry_uncertainty |
| 谱 | eis_id, pellet_id | fixture, temperature_K, raw_uri, fit_version, R_ohm, sigma_S_cm, qc_status |
| 证据 | evidence_id, parent_id, supersedes | acquired_at, finished_at, qc_released_at, uncertainty, reviewer_role |
| 预注册 | lock_id, candidate_A, candidate_B | delta, sign, primary_condition, composition_rules, model_version, locked_at |
同一粉体的多个谱是技术重复。相信息与独立 DFT 通过 structure_family_id 关联，真实样品一般无法一对一映射到原子构型。验收须检验父键存在、确认粉体独立、时间单调和全量原始文件可追溯。pilot/ 只预填身份，不填任何实测字段。

