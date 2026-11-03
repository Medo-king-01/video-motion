"""Free local WAAPI feasibility only: manual seek, no renderer or GPU claim."""
from __future__ import annotations

import json
import subprocess

from conftest import ROOT
from test_gpu_preflight import browser_env

SCRIPT=ROOT/'tools/waapi_preflight.mjs'


def test_cli_help_and_existing_output(tmp_path):
    assert 'Usage:' in subprocess.run(['node',str(SCRIPT),'--help'],capture_output=True,text=True).stdout
    output=tmp_path/'report.json';output.write_text('keep')
    result=subprocess.run(['node',str(SCRIPT),'--out',str(output)],capture_output=True,text=True)
    assert result.returncode!=0 and output.read_text()=='keep'


def test_manual_seek_in_local_chromium(tmp_path):
    report_path=tmp_path/'report.json'
    result=subprocess.run(['node',str(SCRIPT),'--out',str(report_path)],env=browser_env(),capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    report=json.loads(report_path.read_text())
    assert report['status']=='pass' and report['frames']==report['reverseMatches']==30 and report['expectedValues']
    assert 'not a benchmark' in report['limitations']
