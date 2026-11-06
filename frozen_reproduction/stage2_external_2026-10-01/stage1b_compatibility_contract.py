#!/usr/bin/env python3
"""Pure Stage-1B compatibility utilities. NO detector calls."""
from __future__ import annotations
import contextlib, io, math, os, platform, struct, sys
from typing import Any
import numpy as np
import threadpoolctl

EVENT_FIELDS=("t0","t1","lifetime_s","n_frames","peak_area_nm2","mean_area_nm2","peak_amp_nm","volume_nm3","fully_observed")
COMPAT_EXACT_FIELDS=("t0","t1","lifetime_s","n_frames","peak_area_nm2","mean_area_nm2","fully_observed")
DIAGNOSTIC_ONLY_FIELDS=("peak_amp_nm","volume_nm3")
EXACT_FLOAT_FIELDS={"t0","t1","lifetime_s","peak_area_nm2","mean_area_nm2"}

def _finite_float(value:Any,field:str,dataset:str,index:int)->float:
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise RuntimeError(f"{dataset} event {index} field {field} is not numeric: {value!r}")
    x=float(value)
    if not math.isfinite(x): raise RuntimeError(f"{dataset} event {index} field {field} is non-finite: {value!r}")
    return x

def _validate_event(event:Any,dataset:str,index:int)->None:
    if not isinstance(event,dict): raise RuntimeError(f"{dataset} event {index} is not an object")
    if set(event)!=set(EVENT_FIELDS):
        raise RuntimeError(f"{dataset} event {index} schema mismatch: missing={sorted(set(EVENT_FIELDS)-set(event))}, extra={sorted(set(event)-set(EVENT_FIELDS))}")
    for field in EVENT_FIELDS:
        value=event[field]
        if field in EXACT_FLOAT_FIELDS or field in DIAGNOSTIC_ONLY_FIELDS: _finite_float(value,field,dataset,index)
        elif field=="n_frames":
            if isinstance(value,bool) or not isinstance(value,int): raise RuntimeError(f"{dataset} event {index} n_frames is not integer: {value!r}")
        elif field=="fully_observed":
            if not isinstance(value,bool): raise RuntimeError(f"{dataset} event {index} fully_observed is not boolean: {value!r}")

def _float_exact_equal(a:Any,b:Any,field:str,dataset:str,index:int)->bool:
    return _finite_float(a,field,dataset,index).hex()==_finite_float(b,field,dataset,index).hex()

def _ordered_float_key(x:float)->int:
    u=struct.unpack(">Q",struct.pack(">d",float(x)))[0]; mask=(1<<64)-1
    return ((~u)&mask) if (u&(1<<63)) else (u|(1<<63))

def ulp_distance(a:float,b:float)->int:
    if not(math.isfinite(a) and math.isfinite(b)): raise ValueError("ULP distance requires finite values")
    return abs(_ordered_float_key(a)-_ordered_float_key(b))

def _relative_difference(a:float,b:float)->float|None:
    d=abs(b-a)
    if a==0.0: return 0.0 if b==0.0 else None
    return d/abs(a)

def compare_event_lists_stage1b(canonical:Any,regenerated:Any,dataset:str)->dict[str,Any]:
    if not isinstance(canonical,list) or not isinstance(regenerated,list): raise RuntimeError(f"{dataset}: event lists must both be lists")
    for i,e in enumerate(canonical): _validate_event(e,dataset+":canonical",i)
    for i,e in enumerate(regenerated): _validate_event(e,dataset+":regenerated",i)
    exact_diffs=[]
    if len(canonical)!=len(regenerated): exact_diffs.append({"kind":"count","canonical":len(canonical),"regenerated":len(regenerated)})
    n=min(len(canonical),len(regenerated))
    for i in range(n):
        ca,rb=canonical[i],regenerated[i]; fd={}
        for field in COMPAT_EXACT_FIELDS:
            if field in EXACT_FLOAT_FIELDS:
                if not _float_exact_equal(ca[field],rb[field],field,dataset,i): fd[field]={"canonical_hex":float(ca[field]).hex(),"regenerated_hex":float(rb[field]).hex()}
            elif ca[field]!=rb[field]: fd[field]={"canonical":ca[field],"regenerated":rb[field]}
        if fd: exact_diffs.append({"kind":"event","index":i,"field_differences":fd})
    diag={}
    for field in DIAGNOSTIC_ONLY_FIELDS:
        rows=[]; mismatch_count=0; max_abs=0.0; max_rel=0.0; max_rel_defined=False; max_ulp=0
        for i in range(n):
            a=float(canonical[i][field]); b=float(regenerated[i][field])
            if a.hex()==b.hex(): continue
            mismatch_count+=1; ad=abs(b-a); rd=_relative_difference(a,b); ud=ulp_distance(a,b)
            max_abs=max(max_abs,ad); max_ulp=max(max_ulp,ud)
            if rd is not None: max_rel=max(max_rel,rd); max_rel_defined=True
            rows.append({"event_index":i,"canonical":a,"regenerated":b,"canonical_hex":a.hex(),"regenerated_hex":b.hex(),"abs_diff":ad,"relative_diff":rd,"ulp_distance":ud})
        diag[field]={"pass_fail_role":"diagnostic_only","mismatch_count":mismatch_count,"compared_event_count":n,"max_abs_diff":max_abs,"max_relative_diff":max_rel if max_rel_defined else None,"max_ulp_distance":max_ulp,"per_event_mismatches":rows}
    return {"dataset":dataset,"criterion_version":"EventAudit-external-stage1B-compatibility-v1-2026-10-01","criterion_basis":"frozen EventAudit external adapter dependency contract; no fitted numerical tolerance","ordering":"detector output order exact; no sorting, matching, or reassignment","event_count_exact":len(canonical)==len(regenerated),"required_exact_fields":list(COMPAT_EXACT_FIELDS),"diagnostic_only_fields":list(DIAGNOSTIC_ONLY_FIELDS),"compatibility_pass":len(exact_diffs)==0,"exact_field_mismatches":exact_diffs,"numeric_drift_diagnostics":diag,"original_stage1_exact_bitwise_verdict_changed":False}

def capture_numeric_provenance()->dict[str,Any]:
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf): np.show_config()
    return {"python":sys.version,"python_executable":sys.executable,"platform":platform.platform(),"machine":platform.machine(),"numpy_version":np.__version__,"threadpoolctl_version":getattr(threadpoolctl,"__version__",None),"threadpool_info":threadpoolctl.threadpool_info(),"numpy_show_config":buf.getvalue().splitlines(),"thread_related_environment_variables":{k:os.environ.get(k) for k in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","BLIS_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS")}}
