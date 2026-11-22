param([string]$NotesPdf)
$ErrorActionPreference='Stop'
$pptPath=Join-Path $PSScriptRoot '汇报版开题报告_P8.pptx'
$pdfPath=Join-Path $PSScriptRoot '汇报版开题报告_P8.pdf'
$app=New-Object -ComObject PowerPoint.Application
$presentation=$app.Presentations.Open($pptPath,-1,0,0)
try { $presentation.SaveAs($pdfPath,32) } finally { $presentation.Close() }
if ($app.Presentations.Count -eq 0) { $app.Quit() }
if ($NotesPdf) {
  $word=New-Object -ComObject Word.Application
  $word.Visible=$false
  $word.DisplayAlerts=0
  $doc=$word.Documents.Open((Join-Path $PSScriptRoot 'P8_逐页汇报词.docx'),$false,$true)
  try { $doc.ExportAsFixedFormat($NotesPdf,17) } finally { $doc.Close(0); $word.Quit() }
}

