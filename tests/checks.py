"""Offline invariants only. Host dictionaries are synthetic trusted test inputs.
No event authentication, page NLP, production registration or execution exists.
"""
import json,hashlib
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/'aftercare-remedy/references/remedy.schema.json').read_text(encoding='utf-8'))
def validate(name,data):
 Draft202012Validator({'$defs':SCHEMA['$defs'],'$ref':'#/$defs/'+name},format_checker=FormatChecker()).validate(data)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def check(q,r,h):
 validate('aftercare-remedyRequest',q);validate('aftercare-remedyResult',r)
 for k in ['contract_version','skill_id','call_id','task_id']:need(q[k]==r[k],'identity')
 need(q['skill_version']=='1.0.0','skill_version')
 need(q['expected_task_revision']==r['based_on_task_revision']==h['revision'],'revision')
 need(q['mode']==h['mode'] and not h['paused'],'mode_pause')
 for ref in [q['task_snapshot'],*q['inputs'].values()]:
  if ref is None:continue
  row=h['registry'].get(ref['artifact_id']);need(row is not None,'missing_ref')
  need(row['task_id']==q['task_id'],'cross_task')
  need(row['kind']==ref['kind'] and row['revision']==ref['revision'],'ref_kind_revision')
  need(row.get('available',True),'unavailable_ref');validate(ref['kind'],row['data'])
 snap=h['registry'][q['task_snapshot']['artifact_id']]['data']
 need(snap['task_id']==q['task_id'] and snap['task_revision']==h['revision'] and snap['mode']==q['mode'] and not snap['paused'],'snapshot')
 need(snap['intent_ref']==q['inputs']['intent'],'snapshot_intent')
 order=h['registry'][q['inputs']['order']['artifact_id']]['data']
 need(snap['target_item_ref']==order['selected_item_ref'] and snap['selection_receipt_ref']==order['selection_receipt_ref'],'snapshot_order')
 d=r['data'];need(d is not None,'data_required_by_skill')
 ids=[o['option_id'] for o in d['options']];need(len(ids)==len(set(ids)),'duplicate_option')
 need(d['recommended_option_id'] is None or d['recommended_option_id'] in ids,'recommendation_membership')
 for o in d['options']:
  need(h['option_kinds'].get(o['option_id'])==o['kind'],'unsupported_option')
  for f in o['conditions']+o['consequences']:check_fact(f,q,h,order)
 for f in d['material_requirements']:
  check_fact(f,q,h,order)
  need(h['material_levels'].get(f['key']) in ['required','conditional'],'suggestion_as_required')
 chosen=d['chosen_option_id'];receipt=d['choice_receipt_ref']
 need((chosen is None)==(receipt is None),'paired_choice')
 if chosen is not None:
  need(chosen in ids,'choice_membership')
  dec=h['choice_receipts'].get(receipt);need(dec is not None,'missing_choice_receipt');validate('UserDecision',dec)
  need(dec['task_id']==q['task_id'] and dec['decision_kind']=='choose_option','decision_task_kind')
  need(dec['selected_value_ref']==chosen and dec['based_on_task_revision']<=h['revision'],'decision_option_revision')
  supplied=q['inputs']['user_decision']
  need(supplied is not None and h['registry'][supplied['artifact_id']]['data']==dec,'supplied_decision')
  ev=h['choice_events'].get(dec['user_event_ref']);need(ev is not None and ev['source']=='user' and ev['explicit'],'user_event')
  need(ev['subject_ref']==dec['subject_ref'] and ev['selected_value_ref']==chosen,'presentation')
  bind=h['choice_bindings'].get(receipt);need(bind is not None,'missing_binding')
  need(bind['active'] and bind['task_id']==q['task_id'] and bind['item_ref']==order['selected_item_ref'] and bind['account']==h['account'],'choice_invalidated')
  need(bind['validated_revision']==h['revision'] and bind['options_digest']==digest(d['options']),'choice_content_changed')
 # v1 is unconditionally analysis-only: it lacks confirmed-intent/readiness contracts.
 need(not any(s['next_skill_hint'] in ['aftercare-evidence','aftercare-interact'] for s in d['next_steps']),'v1_formal_handoff_closed')
 return {'choice_valid':chosen is not None,'formal_preparation_allowed':False,'submission_authorized':False,'reason':'central_v1_contract_gaps','page_current':h['page_current']}
def check_fact(f,q,h,order):
 for eid in f['evidence_refs']:
  e=h['evidence'].get(eid);need(e is not None,'missing_evidence')
  need(e['task_id']==q['task_id'] and e['item_ref']==order['selected_item_ref'],'evidence_scope')
  need(e.get('current',True),'stale_evidence')
  # Policy requirements cannot derive from an unproven user report or inference.
  need(f['certainty']=='observed' and e.get('source')=='official_order_page','policy_source')
