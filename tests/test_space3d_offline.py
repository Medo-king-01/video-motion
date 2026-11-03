"""Existing native P software 3D as a free, authored-time fallback, not Three parity."""
from __future__ import annotations

import hashlib

import space3d
from PIL import Image, ImageDraw
from render_policy import decorative_time


def test_native_software_3d_frame_seek_and_reduced():
    model=space3d.box(120);camera=space3d.camera(dist=600,yaw=.2,pitch=.1)
    def sample(frame,mode):
        local=decorative_time(frame/30,mode)
        image=Image.new('RGB',(320,320),'#F3F2F1')
        rotated=space3d.transform(model,rx=.25,ry=.2+local)
        faces=space3d.draw_mesh(ImageDraw.Draw(image),rotated,camera,320,320,{'front':'#CB271B','side':'#D5AEA6'},ambient=.8)
        assert faces>0 and image.getpixel((160,160))!=(243,242,241)
        return hashlib.sha256(image.tobytes()).hexdigest()
    forward=[sample(i,'normal') for i in range(30)]
    assert [sample(i,'normal') for i in range(29,-1,-1)]==forward[::-1]
    assert forward[0]!=forward[-1]
    assert all(sample(i,'reduced')==forward[0] for i in (0,15,29))


def test_native_box_faces_point_outward_in_python_and_javascript():
    import json

    from conftest import SKILL
    from test_visual_tools import js

    model=space3d.box(120)
    normals=[]
    for face in model['faces']:
        indices,_=face;normal=space3d.face_normal(model,face)
        centre=[sum(model['verts'][i][axis] for i in indices)/len(indices) for axis in range(3)]
        assert sum(a*b for a,b in zip(normal,centre,strict=True))>0
        normals.append(normal)
    module=(SKILL/'templates/render/lib/space3d.js').as_uri()
    actual=js(f'import {{box,faceNormal}} from {json.dumps(module)};let m=box(120);console.log(JSON.stringify(m.faces.map(f=>faceNormal(m,f))));')
    for expected,computed in zip(normals,actual,strict=True): assert tuple(computed)==expected
