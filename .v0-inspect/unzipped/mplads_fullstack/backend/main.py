import os, sys, json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import database as db
from pipeline import generate_sample_data, data_cleaning, anomaly_detection, risk_engine
from pipeline import real_data
import feedback_store

app = FastAPI(title="MPLADS AI Sentinel API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
BASE=os.path.dirname(__file__); DATA_DIR=os.path.join(BASE,"data"); RAW_DATA_PATH=os.path.join(DATA_DIR,"MPLADS.csv")
SOURCE_NAME="MPLADS work-record development snapshot"

def run_pipeline(raw, source_name=SOURCE_NAME):
    clean=raw.copy()
    clean=anomaly_detection.compute_cost_anomaly(clean, group_cols=("state","sector"))
    clean=anomaly_detection.compute_delay_anomaly(clean)
    clean=anomaly_detection.compute_duplicate_scores(clean, group_col="constituency")
    clean=anomaly_detection.compute_overall_confidence(clean)
    final=risk_engine.build_final_table(clean, weights=feedback_store.load_weights())
    final["source_name"]=source_name; final["source_snapshot"]=datetime.now(timezone.utc).isoformat(); final["review_status"]="New"; final["investigator_note"]=""
    return final

def load_real(): return real_data.load(RAW_DATA_PATH)

def build_dataset():
    if os.path.exists(RAW_DATA_PATH):
        raw=load_real(); source=SOURCE_NAME
    else:
        raw_path=os.path.join(DATA_DIR,"raw_mplads_sample.csv")
        if not os.path.exists(raw_path): generate_sample_data.run(output_dir=DATA_DIR)
        raw=data_cleaning.clean(data_cleaning.load_raw(raw_path)); source="Synthetic demonstration dataset"
    final=run_pipeline(raw,source)
    now=datetime.now(timezone.utc).isoformat(); changes,new_count=db.detect_changes(final,now,source)
    db.bulk_insert_projects(final); db.record_project_snapshots(final,now,source)
    max_date=raw["date_of_administrative_approval"].max() if "date_of_administrative_approval" in raw else None
    db.record_ingestion(source,now,max_date.isoformat() if pd.notna(max_date) else None,len(final),len(changes),new_count, [c for c in ["expenditure","physical_progress_percent","expected_completion_date","latitude","longitude","district"] if c not in raw.columns or raw[c].isna().all()])
    return final

@app.on_event("startup")
def startup():
    db.init_db()
    if db.is_empty(): build_dataset()

class FeedbackIn(BaseModel): work_id:str; verdict:str
class ReviewIn(BaseModel): work_id:str; status:str|None=None; note:str|None=None

@app.get('/api/health')
def health(): return {"status":"ok","time":datetime.now(timezone.utc).isoformat(),"source":db.latest_ingestion()}
@app.get('/api/stats')
def stats(): return db.get_stats()
@app.get('/api/filters')
def filters(): return db.get_filter_options()
@app.get('/api/projects')
def projects(state:str=None,district:str=None,sector:str=None,min_score:float=0,search:str=None,sort_by:str='risk_score',sort_dir:str='desc',limit:int=Query(50,le=200),offset:int=0):
    rows,total=db.query_projects(state,district,sector,min_score,search,sort_by,sort_dir,limit,offset)
    for r in rows:r['reasons']=json.loads(r.pop('reasons_json') or '[]')
    return {'total':total,'limit':limit,'offset':offset,'projects':rows}
@app.get('/api/projects/{work_id}')
def project(work_id:str):
    r=db.get_project(work_id)
    if not r: raise HTTPException(404,'Project not found')
    r['reasons']=json.loads(r.pop('reasons_json') or '[]'); return r
@app.get('/api/entities')
def entities(type:str=Query('mp',pattern='^(mp|agency)$'),min_works:int=2): return db.entity_leaderboard('mp_name' if type=='mp' else 'implementing_agency_name',min_works)
@app.get('/api/weights')
def weights(): return feedback_store.feedback_summary()
@app.get('/api/source-status')
def source_status():
    x=db.latest_ingestion() or {}; return {'source':x.get('source_name'), 'last_ingestion':x.get('snapshot_time'),'source_max_date':x.get('source_max_date'),'records':x.get('record_count'),'new_records':x.get('new_count'),'changed_fields':x.get('changed_count'),'missing_fields':json.loads(x.get('missing_fields_json') or '[]'),'freshness':'Current snapshot available; awaiting newer authoritative publication.'}
@app.get('/api/changes')
def changes(limit:int=Query(100,le=500)): return db.recent_changes(limit)
@app.get('/api/spatial')
def spatial():
    with db.get_conn() as conn:
        rows=[dict(r) for r in conn.execute("SELECT work_id,work_name,state,constituency,latitude,longitude,risk_score,risk_level FROM projects WHERE latitude IS NOT NULL AND longitude IS NOT NULL LIMIT 5000").fetchall()]
    return {'available':bool(rows),'projects':rows,'note':'Only published coordinates are shown; no spatial fraud conclusion is inferred.'}
@app.get('/api/validation')
def validation():
    with db.get_conn() as conn:
        row=conn.execute("SELECT COUNT(*) n,SUM(CASE WHEN is_planted_anomaly=1 THEN 1 ELSE 0 END) planted FROM projects").fetchone()
        n=row['n']; planted=row['planted'] or 0
    return {'evaluation_type':'controlled synthetic labels' if planted else 'not measured','projects':n,'labelled_test_anomalies':planted,'note':'These are development-data metrics, not real-world fraud-detection performance.'}
@app.post('/api/feedback')
def feedback(payload:FeedbackIn):
    if payload.verdict not in ('confirmed','false_positive'): raise HTTPException(400,'Invalid verdict')
    p=db.get_project(payload.work_id)
    if not p: raise HTTPException(404,'Project not found')
    scores={k:p.get(k) or 0 for k in ['cost_anomaly_score','delay_anomaly_score','duplicate_score','progress_mismatch_score']}
    nw=feedback_store.record_feedback(payload.work_id,payload.verdict,scores)
    df=db.get_all_projects_df(); df=risk_engine.compute_risk_score(df,nw); df['reasons']=df.apply(risk_engine.generate_reasons,axis=1); df['risk_level']=df.risk_score.apply(risk_engine.risk_level); db.bulk_update_scores(df); db.update_review(payload.work_id,'Confirmed' if payload.verdict=='confirmed' else 'False Positive')
    up=db.get_project(payload.work_id); up['reasons']=json.loads(up.pop('reasons_json') or '[]'); return {'weights':nw,'updated_project':up}
@app.post('/api/review')
def review(payload:ReviewIn):
    if payload.status not in (None,'New','Under Review','Confirmed','False Positive'): raise HTTPException(400,'Invalid status')
    if not db.get_project(payload.work_id): raise HTTPException(404,'Project not found')
    db.update_review(payload.work_id,payload.status,payload.note); return db.get_project(payload.work_id)
@app.post('/api/ingest')
async def ingest(file:UploadFile=File(...)):
    if not file.filename.lower().endswith('.csv'): raise HTTPException(400,'Upload a CSV file')
    raw_bytes=await file.read()
    if len(raw_bytes)>25*1024*1024: raise HTTPException(413,'CSV exceeds 25 MB limit')
    tmp=os.path.join(DATA_DIR,'incoming.csv'); os.makedirs(DATA_DIR,exist_ok=True); open(tmp,'wb').write(raw_bytes)
    try:
        raw=real_data.load(tmp)
    except Exception as e: raise HTTPException(400,f'Could not parse MPLADS CSV: {e}')
    final=run_pipeline(raw,f'Uploaded: {file.filename}'); now=datetime.now(timezone.utc).isoformat(); changes,new_count=db.detect_changes(final,now,file.filename); db.bulk_insert_projects(final); db.record_project_snapshots(final,now,file.filename)
    max_date=raw.date_of_administrative_approval.max() if 'date_of_administrative_approval' in raw else None
    missing=[c for c in ['expenditure','physical_progress_percent','expected_completion_date','latitude','longitude','district'] if c not in raw.columns or raw[c].isna().all()]
    db.record_ingestion(file.filename,now,max_date.isoformat() if pd.notna(max_date) else None,len(final),len(changes),new_count,missing)
    return {'status':'screened','source':file.filename,'records':len(final),'new_records':new_count,'changed_fields':len(changes),'missing_fields':missing}
