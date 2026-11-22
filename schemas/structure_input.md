# 构型、标签与谱系接口 v1

从结构库、CIF、POSCAR 或 extxyz 导入时保留原文件 SHA256。CIF 与 POSCAR 默认仅携带结构；每个 DFT 标签必须回到带相同 frame_id 的计算记录。导出采用 DeePMD NumPy。四种源格式并不共享标签语义。此处约定用于后续转换与训练，当前未生成 LPSC 的标签。

|物理量|目录 / 文件|约定|
|---|---|---|
|类型|system/type_map.raw, type.raw|符号词表与 N 个零起始整数 ID。各帧坐标、力、类型同序；读取器须按符号将局部词表映到权重的完整词表，禁止重排检查点的类型嵌入|
|晶胞|set.*/box.npy|每帧 9 个数，行序 aₓ,aᵧ,a_z,bₓ,…,c_z，Å|
|坐标|set.*/coord.npy|B×3N 展平，每帧 N 个 Cartesian 三元组，Å；输入 POSCAR 分数坐标先乘胞矩阵|
|能量|set.*/energy.npy|B 个体系总能量，eV。必须记录能量参考、赝势和电子设置|
|力|set.*/force.npy|B×3N，eV/Å；与 coord 对齐，定义为负梯度|
|virial|set.*/virial.npy|可选，B×9，顺序 xx,xy,xz,yx,yy,yz,zx,zy,zz，单位 eV；参考应力单位需转为 eV/Å³，再乘体积并处理号|
|混合类型|set.*/real_atom_types.npy|B×Nslots 类型；type.raw 全零占位，type_map.raw 必填。−1 是虚原子，力填零并在指标、池化及损失里排除|
|定位与划分|伴随的帧清单|frame_id, source_hash, parent_id, lineage_id, trajectory_id, time_ps, site_family, formula, x, reference_id, group_id, split, label_kind={DFT,teacher,unlabeled}|

标准 system 按组成与原子数分开。混合输入应先对同总槽位的 toy system 做逐帧与常规格式一致性测试，混合不同 N 时再补虚原子。v3.2.0 的数据通用页面仍仅列举早期描述符，但 DPA4 专页明确列出 mixed-type。首轮优先按真实 system 分组。[数据目录](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/data/system.md) · [NumPy 数据格式](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/data/data-conv.md) · [DPA4 数据说明](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/model/dpa4.md#data-format)

接收测试为晶胞有正体积、坐标/力全部有限、每帧真实计量与来源一致、同原型及轨迹组不跨 split、同 frame_id 只有一份同口径主标签。重算结果另加 reference_id。教师标签不能出现在独立 DFT 测试集。
