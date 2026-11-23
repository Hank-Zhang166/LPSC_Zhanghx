"""Assemble a standalone technical appendix while retaining repository-relative source links."""
from pathlib import Path
import os,re
ROOT=Path(__file__).resolve().parents[1]
sections=[
 ('研究问题与可否定的比较',['docs/RESEARCH_QUESTION.md','docs/MATERIAL_DOMAIN.md','docs/COMPARISONS.md']),
 ('可复核的数据与引用',['docs/DATA_AUDIT.md','refs/EVIDENCE_SOURCES.md']),
 ('模型、输入输出与参数更新',['docs/DPA4_ARCHITECTURE.md','docs/MODEL_TRAINING.md','docs/VALIDATION_PROTOCOL.md','docs/DISTILLATION_DECISION.md']),
 ('逐模式实验卡',['experiments/README.md']+[f'experiments/cards/M{i}.md' for i in range(7)]),
 ('实验先导与数据契约',['docs/WET_EXPERIMENT.md','schemas/structure_input.md','schemas/wet_sample.md','schemas/model_registry.md','schemas/task_event.md']),
 ('事件仿真、数值和可复算证明',['docs/DES_SPEC.md','docs/DES_RESULTS.md','simulation/README.md']),
 ('版本质量和后续验收',['paper/P8_CLAIM_AUDIT.md','tests/TEST_PLAN.md','docs/REPRODUCIBILITY.md'])]
parts=['# P8 技术附录','本附录对应《氯富集硫银锗矿的输运分歧与序贯验证》。引用核查、公开文件复算、仿真结果与下一阶段计划各自标示。基准 V0 使用 5,000 个配对随机种子；可变参数、数据谱系和原始结果保存在同一仓库。','[书面报告](paper/开题报告_P8.pdf) · [汇报版](paper/汇报版开题报告_P8.pdf) · [P7 双稿逐页修改对照](paper/P7_TO_P8_CHANGELOG.md) · [公开数据清单](configs/dataset_manifest.csv) · [仿真假设](configs/assumptions.yaml) · [参数证据来源](simulation/evidence_sources.csv)']
parts.append('文字稿第 2.1 节综述 67 篇学术文献，原子标签库中缺少 x=0.25/0.50 与文献已有相应湿端测量是两项独立判断。可按正文引文编号查逐篇证据，再按文献、工艺、温度、测量对象查外部对照。最终确认采用锁定预测后的新粉体。[综述证据表](refs/literature_review.csv) · [历史输运记录](refs/literature_transport_benchmarks.csv)')
for idx,(name,files) in enumerate(sections,1):
    parts.append(f'## {idx}　{name}')
    for rel in files:
        source=ROOT/rel
        lines=source.read_text('utf-8-sig').splitlines()
        def rebase(m):
            link=m[1]
            if '://' in link or link.startswith(('#','mailto:')):return m[0]
            local,sep,frag=link.partition('#')
            loc=os.path.relpath((source.parent/local).resolve(),ROOT).replace('\\','/')
            return ']('+loc+(sep+frag if sep else '')+')'
        fence=False
        for i,line in enumerate(lines):
            if line.startswith(('`' * 3,'~~~')):fence=not fence;continue
            if not fence:
                if line.startswith('#'):line='##'+line
                line=re.sub(r'\]\(([^)\s]+)\)',rebase,line)
                lines[i]=line
        parts.append('\n'.join(lines))
(ROOT/'P8_技术附录.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')

