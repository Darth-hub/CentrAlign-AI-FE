"""Explicit local demo quote input; creates no ERP orders and changes no old data."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from datetime import date, timedelta
from services.database import initialize
from services.dynamo import get_item, put_item
from services.supplier_quotes import SupplierQuote, get_quote_context
from services.auth import current_claims
from adapters.canonical_api import _get_adapter, Caller

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--requisition', required=True)
parser.add_argument('--allow-synthetic-demo', action='store_true')
args = parser.parse_args()
if not args.allow_synthetic_demo:
    raise SystemExit('Explicit --allow-synthetic-demo is required; these are not real supplier quotes.')
# This operator-only setup script uses the already provisioned demo ERP identity.
email = 'demo+jake@example.com'
current_claims.set({'email': email, 'p2p_role': 'procurement', 'sub': 'demo-quote-setup'})
adapter = _get_adapter(Caller(email=email, allow_service_account=False))
request = adapter.get_requisition(args.requisition)
if {line.item_id for line in request.line_items} != {'MAT-SF-001','MAT-SF-002'} or request.currency != 'USD':
    raise SystemExit('This fixture supports only the USD safety-PPE request; no data was created.')
initialize()
today = date.today()
for suffix, supplier, prices, days in [
    ('SAFETY','SafetyFirst Equipment Co', {'MAT-SF-001':11.5,'MAT-SF-002':14.0},7),
    ('MRO','MRO Warehouse Direct', {'MAT-SF-001':12.0,'MAT-SF-002':14.5},10),
]:
    vendor = adapter.get_supplier(supplier)
    if vendor.status != 'active':
        raise SystemExit('Fixture supplier is not active; no quote for that supplier was added.')
    quote_id = 'DEMO-QUOTE-' + args.requisition + '-' + suffix
    existing = get_item('supplier-quotes', {'quote_id': quote_id})
    if existing:
        print(quote_id + ': preserving existing quote (no automatic renewal or overwrite).')
        continue
    quote = SupplierQuote(quote_id=quote_id,requisition_id=args.requisition,supplier_id=supplier,
        source='synthetic-demo',label='SYNTHETIC DEMO INPUT — not a real supplier commitment or historical order',
        valid_from=today,valid_until=today+timedelta(days=30),currency='USD',payment_terms='Net 30',delivery_days=days,
        line_items=[{'item_id':line.item_id,'quantity':line.quantity,'unit_price':prices[line.item_id],
                     'unit_of_measure':line.unit_of_measure} for line in request.line_items])
    put_item('supplier-quotes',quote.model_dump(mode='json'))
    print(quote_id + ': stored synthetic demo input.')
context=get_quote_context(args.requisition)
for quote in context['quotes']:
    print(quote['quote_id'],quote['supplier_id'],'USD',quote['quoted_total'],'delivery days',quote['delivery_days'])
print('Human review required:',context['requires_human_approval'])
