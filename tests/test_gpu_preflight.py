"""Optional, local-only graphics capability probe and fail-closed CLI."""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest
from conftest import ROOT

SCRIPT = ROOT / 'tools/gpu_preflight.mjs'


def node(*args, **kwargs):
    if not shutil.which('node'): pytest.skip('Node is unavailable')
    return subprocess.run(['node', str(SCRIPT), *args], capture_output=True, text=True, timeout=90, **kwargs)


def test_cli_help_and_invalid_requirement():
    assert 'Usage:' in node('--help').stdout
    assert node('--require', 'hardware').returncode != 0
    assert node('--unknown').returncode != 0


def test_report_output_refuses_to_overwrite(tmp_path):
    output = tmp_path / 'existing.json'; output.write_text('keep')
    result = node('--out', str(output))
    assert result.returncode != 0
    assert output.read_text() == 'keep'


def test_dangling_symlink_output_is_not_followed(tmp_path):
    output = tmp_path / 'report.json'; target = tmp_path / 'target.json'; output.symlink_to(target)
    # The exclusive write may happen after the probe; skip if the shared browser is unavailable.
    result = node('--out', str(output), env=browser_env())
    assert result.returncode != 0 and not target.exists() and output.is_symlink()


def browser_env():
    toolkit = ROOT / 'tools/toolkit'
    if not shutil.which('node') or not (toolkit / 'node_modules/playwright-core').exists():
        pytest.skip('Shared K toolkit unavailable')
    result = subprocess.run(['node', str(ROOT/'tools/chromium.mjs'), '--json'], capture_output=True, text=True, timeout=90)
    if result.returncode: pytest.skip('Shared Chromium unavailable')
    config = json.loads(result.stdout)
    return {**os.environ, 'MEDO_TOOLKIT': str(toolkit), 'MEDO_CHROMIUM': config['executablePath'],
            'LD_LIBRARY_PATH': (config.get('libraryPath') or '') + ':' + os.environ.get('LD_LIBRARY_PATH', '')}


def test_real_local_browser_probe_and_requirement_gate(tmp_path):
    env = browser_env(); output = tmp_path / 'probe.json'
    result = node('--out', str(output), '--require', 'both', env=env)
    assert output.is_file(), result.stderr
    report = json.loads(output.read_text())
    assert report['version'] == 1 and report['browserVersion']
    for api in ('webgl2', 'webgpu'):
        assert report[api]['status'] in ('pass', 'unavailable', 'fail', 'timeout')
        assert report[api]['softwareIndicator'] in ('detected', 'unknown')
        assert not any(key in report[api] for key in ('vendor', 'renderer', 'device', 'architecture', 'description'))
    if report['webgl2']['status'] == 'pass':
        assert report['webgl2']['knownPixelValid'] and report['webgl2']['reverseMatches'] == 3
    if report['webgpu']['status'] == 'pass': assert report['webgpu']['computeResultValid']
    expected = 0 if report['webgl2']['status'] == report['webgpu']['status'] == 'pass' else 1
    assert result.returncode == expected, result.stderr
    assert 'does not prove hardware' in report['limitations']


def test_mock_webgpu_compute_success_error_and_cleanup():
    if not shutil.which('node'): pytest.skip('Node is unavailable')
    module = (ROOT / 'tools/lib/gpu_probe.mjs').as_uri()
    code = f'''import {{probeGraphics}} from {json.dumps(module)};
      globalThis.document={{createElement:()=>({{getContext:()=>null}})}};
      globalThis.GPUBufferUsage={{STORAGE:1,COPY_SRC:2,MAP_READ:4,COPY_DST:8}};
      globalThis.GPUMapMode={{READ:1}};let disposed=0,fail=false;
      const buffer=()=>({{destroy(){{disposed++}},mapAsync:async()=>{{}},getMappedRange:()=>new Uint32Array([42]).buffer,unmap(){{}}}});
      const device={{pushErrorScope(){{}},popErrorScope:async()=>null,createBuffer:buffer,
        createShaderModule:()=>({{}}),createComputePipelineAsync:async()=>{{if(fail)throw Error('sensitive adapter id');return {{getBindGroupLayout:()=>({{}})}}}},
        createBindGroup:()=>({{}}),createCommandEncoder:()=>({{beginComputePass:()=>({{setPipeline(){{}},setBindGroup(){{}},dispatchWorkgroups(){{}},end(){{}}}}),copyBufferToBuffer(){{}},finish:()=>({{}})}}),
        queue:{{submit(){{}}}},destroy(){{disposed++}}}};
      Object.defineProperty(globalThis,'navigator',{{value:{{gpu:{{requestAdapter:async()=>({{info:{{description:'SwiftShader secret'}},requestDevice:async()=>device}})}}}}}});
      const ok=await probeGraphics();fail=true;const bad=await probeGraphics();
      console.log(JSON.stringify({{ok,bad,disposed}}));'''
    result = subprocess.run(['node', '--input-type=module', '-e', code], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data['ok']['webgpu']['status'] == 'pass' and data['ok']['webgpu']['computeResultValid']
    assert data['ok']['webgpu']['softwareIndicator'] == 'detected'
    assert data['bad']['webgpu']['status'] == 'fail' and 'sensitive' not in result.stdout
    assert data['disposed'] == 6
