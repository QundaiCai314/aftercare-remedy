"""Proposed assessment diagnostics, not a runtime release or authorization gate."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker,ValidationError
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text(encoding='utf-8'))
def semantic_errors(a):
 errors=[]
 if a['preparation']['state']=='ready_for_preparation':
  if a['choice_binding_ref'] is None:errors.append('choice_missing')
  if a['preparation']['blocker_codes']:errors.append('unresolved_blockers')
  if any(c['state']=='unresolved' for c in a['conflicts']):errors.append('conflict')
  if not a['options']:errors.append('no_options')
  # Deliberately conservative: full selected-option binding is a pending runtime requirement.
  for o in a['options']:
   if o['availability']!='available' or any(c['state']!='met' for c in o['condition_checks']):errors.append('conditions_unknown')
   if any(o[k]['state']=='unknown' for k in ['refund_amount','return_fee','deadline','return_required']):errors.append('important_terms_unknown')
 return errors
if __name__=='__main__':
 schema=read('candidate/remedy-assessment.schema.json');Draft202012Validator.check_schema(schema)
 v=Draft202012Validator(schema,format_checker=FormatChecker());out=[]
 for name,valid in [('positive.json',True),('negative-unknown-fee-zero.json',False),('negative-missing-condition.json',False),('negative-ready-with-unknown.json',True)]:
  a=read('candidate/'+name);errors=list(v.iter_errors(a));assert (not errors)==valid
  sem=semantic_errors(a) if valid else []
  if name=='negative-ready-with-unknown.json':assert sem
  elif valid:assert not sem
  out.append({'file':name,'schema_accepted':not errors,'semantic_errors':sem,'expected_behavior':True})
 (R/'tests/candidate-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Four candidate examples checked; candidate remains unadopted')
