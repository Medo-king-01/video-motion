"""Portable, read-only configuration resolution. No machine-specific paths."""
import os,json,pathlib,shutil
SKILL=pathlib.Path(__file__).resolve().parents[1]
def config():
 p=pathlib.Path(os.environ.get('KHAAM_CONFIG',str(pathlib.Path.cwd()/'.khaam/config.json'))).expanduser()
 if not p.exists():return {},p.parent.parent
 d=json.loads(p.read_text(encoding='utf-8-sig'))
 if not isinstance(d,dict):raise ValueError('Khaam config must be a JSON object')
 return d,p.parent.parent
def resolve(key,env,default=None):
 d,base=config();value=os.environ.get(env) or d.get(key) or default
 if value is None:return None
 p=pathlib.Path(os.path.expandvars(str(value))).expanduser()
 return p.resolve() if p.is_absolute() else (base/p).resolve()
def models_dir():return resolve('models_dir','KHAAM_MODELS',str(pathlib.Path.home()/'.cache/khaam-motion/models'))
def sfx_library():return resolve('sfx_library','KHAAM_SFX_LIBRARY',str(__import__('pathlib').Path.cwd()/'assets/sfx'))
def executable(name):
 d,_=config();override=os.environ.get('KHAAM_'+name.upper()) or d.get(name)
 if override:
  candidate=resolve(name,'KHAAM_'+name.upper())
  if candidate.is_file():return str(candidate)
  return shutil.which(str(override))
 return shutil.which(name)
