"""Check document synchronization, package integrity and the pre-registered experimental units."""
import csv,re,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'paper'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def normalized(s):
    return ''.join(s.split())
outline=(PAPER/'P8_OUTLINE.md').read_text('utf-8')
titles=[line.split('. ',1)[1].split(' —— ')[0] for line in outline.splitlines() if re.match(r'^\d+\. ',line)]
slides=PdfReader(PAPER/'汇报版开题报告_P8.pdf')
paper=PdfReader(PAPER/'开题报告_P8.pdf')
assert len(slides.pages)==len(titles)
with zipfile.ZipFile(PAPER/'汇报版开题报告_P8.pptx') as z:
    assert z.testzip() is None
    entries=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
    assert len(entries)==len(titles)
    for i,title in enumerate(titles,1):
        text=''.join(n.text or '' for n in ET.fromstring(z.read(f'ppt/slides/slide{i}.xml')).iter(A+'t'))
        assert normalized(title) in normalized(text),(i,title)
        assert normalized(title) in normalized(slides.pages[i-1].extract_text()),(i,'PDF title')
        assert f'ppt/notesSlides/notesSlide{i}.xml' in z.namelist()
with zipfile.ZipFile(PAPER/'P8_逐页汇报词.docx') as z:
    assert z.testzip() is None
    root=ET.fromstring(z.read('word/document.xml'))
    paragraphs=[''.join(n.text or '' for n in p.iter(W+'t')) for p in root.iter(W+'p')]
    for i,title in enumerate(titles,1):
        idx=paragraphs.index(f'{i:02d}　{title}')
        assert len(paragraphs[idx+1])>55,(i,'speaking notes')
with zipfile.ZipFile(PAPER/'开题报告_P8.docx') as z:assert z.testzip() is None
paper_text=normalized(''.join(p.extract_text() for p in paper.pages))
for needle in ['28,100','131,670','0.247','5,000','独立确认','OBELiX','参考文献']:
    assert normalized(needle) in paper_text,needle
for marker in ['@BASE_TABLE','@DELTA_TABLE','@ABLATION_TABLE']:assert marker not in paper_text

def citation_numbers(source):
    cited=set()
    for cluster in re.findall(r'\[([1-9]\d*(?:[,–-][1-9]\d*)*)\]',source):
        for block in cluster.split(','):
            ends=[int(v) for v in re.split('[–-]',block)]
            cited.update(range(ends[0],ends[-1]+1))
    return cited

chapter=(PAPER/'manuscript.md').read_text('utf-8')
rest,bibliography=(PAPER/'manuscript_des.md').read_text('utf-8').split('## 参考文献与可复核资料',1)
bibliography=bibliography.split('## 附录',1)[0]
entries=[int(v) for v in re.findall(r'^\[(\d+)\] ',bibliography,re.M)]
assert entries==list(range(1,len(entries)+1))
assert citation_numbers(chapter+rest)==set(entries),'Reference list and in-text citations disagree'
sources=list(csv.DictReader((ROOT/'refs/literature_review.csv').open(encoding='utf-8-sig')))
review=chapter.split('### 2.1 ',1)[1].split('### 2.2 ',1)[0]
review_ids={int(r['ref_no']) for r in sources}
assert len(sources)==len(review_ids)>50 and review_ids<=citation_numbers(review)
with zipfile.ZipFile(PAPER/'开题报告_P8.docx') as z:
    xml=ET.fromstring(z.read('word/document.xml'))
    bookmarks={b.get(W+'name') for b in xml.iter(W+'bookmarkStart')}
    assert {'Biblio'+str(i) for i in entries}<=bookmarks
    assert all(l.get(W+'anchor') in bookmarks for l in xml.iter(W+'hyperlink') if (l.get(W+'anchor') or '').startswith('Biblio'))
powders=list(csv.DictReader((ROOT/'pilot/powders.csv').open(encoding='utf-8-sig')))
pellets=list(csv.DictReader((ROOT/'pilot/pellets.csv').open(encoding='utf-8-sig')))
assert len({r['powder_id'] for r in powders})==10 and len({r['pellet_id'] for r in pellets})==16
assert {r['powder_id'] for r in pellets}=={r['powder_id'] for r in powders}
assert all(r['status']=='planned' for r in powders+pellets)
print(f'PASS: {len(paper.pages)} written pages, {len(titles)} PDF slides / PPT slides / note blocks, 10 planned powders and 16 planned pellets.')

