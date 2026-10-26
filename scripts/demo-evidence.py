"""Capture local demo evidence without printing credentials or changing ERP data.

Run inside the API container. Identity comes from an existing server-verified job,
never from user-supplied email or roles. A duplicate probe is allowed only after
an independently verified PO and must be rejected before enqueueing another job.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from datetime import datetime,timezone
from sqlalchemy import select
from services.database import engine,jobs,events
from services.auth import current_claims,mint_internal_token
from services.lifecycle import get_lifecycle
from services.write_policy import confirmed_po
from adapters.canonical_api import _get_adapter,Caller
from config import settings

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--job',required=True)
parser.add_argument('--check-duplicate',action='store_true')
parser.add_argument('--output')
args=parser.parse_args()
with engine.connect() as conn:
    row=conn.execute(select(jobs).where(jobs.c.id==args.job)).mappings().one()
    progress=[json.loads(body) for body in conn.execute(select(events.c.body).where(events.c.job_id==args.job).order_by(events.c.sequence)).scalars()]
envelope=json.loads(row['payload'])
assert row['kind']=='workflow', 'Choose a workflow job as evidence.'
identity=envelope['identity']; document=envelope['input']['document_id']
current_claims.set(identity)
adapter=_get_adapter(Caller(email=identity['email'],allow_service_account=False))
request=adapter.get_requisition(document)
lifecycle=get_lifecycle(document) or {}
evidence={'captured_at':datetime.now(timezone.utc).isoformat(),
    'environment':'local Docker; synthetic demo tenant',
    'model':{'provider':settings.llm_provider,'model':settings.llm_model},
    'job':{'id':row['id'],'status':row['status'],'owner':row['owner']},
    'request':request.model_dump(mode='json',exclude_none=True),
    'lifecycle_status':lifecycle.get('status'),
    'approval':{'actor':lifecycle.get('approved_by'),'time':lifecycle.get('approved_at')},
    'progress':[{'step':e.get('step'),'agent':e.get('agent'),'tool':e.get('tool')} for e in progress if e.get('type')=='progress'],
    'runs':lifecycle.get('runs',[])}
# Generic key lookup: SQL records use the permanent po:<request> claim key.
from services.database import records
with engine.connect() as conn:
    body=conn.execute(select(records.c.body).where(records.c.collection=='write-claims',records.c.key==f'po:{document}')).scalar()
evidence['write_claim']=json.loads(body) if body else None
if lifecycle.get('status')=='PO_CREATED':
    order=confirmed_po(adapter,document)
    evidence['erp_purchase_order']=order.model_dump(mode='json',exclude_none=True)
    evidence['erp_url']='http://localhost:8080/app/purchase-order/'+order.order_id
    if args.check_duplicate:
        import requests
        def count_orders():
            return len([po for po in adapter.list_purchase_orders().purchase_orders
                if any(line.requisition_id==document for line in po.line_items)])
        before=count_orders()
        response=requests.post('http://localhost:8000/api/agents/workflow/runs',
            headers={'Authorization':'Bearer '+mint_internal_token(identity)},json={'document_id':document},timeout=20)
        after=count_orders()
        evidence['duplicate_probe']={'http_status':response.status_code,
            'detail':response.json().get('detail'), 'orders_before':before,'orders_after':after,
            'passed':response.status_code==409 and before==after==1}
        assert evidence['duplicate_probe']['passed'], 'Duplicate protection verification failed'
else:
    evidence['erp_purchase_order']=None
    if args.check_duplicate:raise SystemExit('No completed verified PO yet; duplicate probe was not run.')
text=json.dumps(evidence,indent=2,default=str)
if args.output:
    Path(args.output).write_text(text+'\n')
    print('Saved evidence for',document,'job',row['id'],'status',lifecycle.get('status'))
else:
    print(text)
