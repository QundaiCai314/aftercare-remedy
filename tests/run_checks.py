import copy,json,hashlib,importlib.util,sys,tempfile,argparse
from pathlib import Path
from jsonschema import ValidationError
from checks import ROOT,SCHEMA,check,validate
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def main(integration):
 report={'schema':[],'invariants':[],'behavior':{'method':'author_walkthrough','independent_model_test':'not_run'},'integration':{'status':'not_run'}}
 paths={}
 report['source_integrity']='not_run: upstream source files are not distributed in the public repository'
 if integration:
  config=ROOT/'tests/source-paths.local.json'
  if not config.exists():raise SystemExit('Integration requires tests/source-paths.local.json; see README.md')
  paths=json.loads(config.read_text(encoding='utf-8'))
  central=json.loads((Path(paths['central'])/'contracts.schema.json').read_text(encoding='utf-8-sig'))
  assert all(d==central['$defs'][n] for n,d in SCHEMA['$defs'].items())
  report['source_integrity']='17 derived definitions match supplied central schema; upstream authenticity not independently established'
 cases=read('tests/cases.json')
 for c in cases:
  validate('aftercare-remedyRequest',c['request']);validate('aftercare-remedyResult',c['author_output'])
  report['schema'].append({'case':c['id'],'result':'pass'})
  try:v=check(c['request'],c['author_output'],c['host'])
  except ValueError as e:
   assert c['id'].startswith('17-');report['invariants'].append({'case':c['id'],'rejected':str(e)})
  else:
   assert not c['id'].startswith('17-');report['invariants'].append({'case':c['id'],'result':v})
 f=read('tests/choice-positive-fixture.json')
 assert check(f['request'],f['author_output'],f['host'])['choice_valid']
 def reject(name,fn):
  x=copy.deepcopy(f);fn(x)
  try:check(x['request'],x['author_output'],x['host'])
  except (ValueError,ValidationError) as e:report['invariants'].append({'case':name,'rejected':str(e).splitlines()[0]});return
  raise AssertionError('incorrectly accepted '+name)
 reject('no_receipt',lambda x:x['host']['choice_receipts'].clear())
 reject('half_choice',lambda x:x['author_output']['data'].update(choice_receipt_ref=None))
 reject('not_member',lambda x:x['author_output']['data'].update(chosen_option_id='another'))
 reject('wrong_recommendation',lambda x:x['author_output']['data'].update(recommended_option_id='another'))
 reject('duplicate_option',lambda x:x['author_output']['data']['options'].append(copy.deepcopy(x['author_output']['data']['options'][0])))
 reject('page_forged_event',lambda x:x['host']['choice_events']['event-choice'].update(source='page'))
 reject('ambiguous_event',lambda x:x['host']['choice_events']['event-choice'].update(explicit=False))
 reject('wrong_presentation',lambda x:x['host']['choice_events']['event-choice'].update(subject_ref='old'))
 reject('wrong_decision_kind',lambda x:x['host']['choice_receipts']['choice-demo'].update(decision_kind='select_item'))
 reject('receipt_cross_task',lambda x:x['host']['choice_receipts']['choice-demo'].update(task_id='other'))
 reject('user_changed_mind',lambda x:x['host']['choice_bindings']['choice-demo'].update(active=False))
 reject('new_target',lambda x:x['host']['choice_bindings']['choice-demo'].update(item_ref='item-b'))
 reject('account_changed',lambda x:x['host'].update(account='other'))
 reject('old_binding_revision',lambda x:x['host']['choice_bindings']['choice-demo'].update(validated_revision=3))
 for key in ['amount','fee','deadline','return_obligation']:
  reject('changed_'+key,lambda x,k=key:x['author_output']['data']['options'][0]['missing_facts'].append(k+'-changed'))
 reject('unknown_evidence',lambda x:x['host']['evidence'].pop('ev-rule'))
 reject('cross_item_evidence',lambda x:x['host']['evidence']['ev-rule'].update(item_ref='other'))
 reject('stale_evidence',lambda x:x['host']['evidence']['ev-rule'].update(current=False))
 reject('merchant_as_policy',lambda x:x['host']['evidence']['ev-rule'].update(source='merchant'))
 reject('report_as_policy',lambda x:x['author_output']['data']['options'][0]['conditions'][0].update(certainty='user_reported'))
 reject('suggestion_as_requirement',lambda x:x['host']['material_levels'].update(photo='suggested'))
 reject('late_result',lambda x:x['host'].update(revision=5))
 reject('pause',lambda x:x['host'].update(paused=True))
 reject('wrong_call',lambda x:x['author_output'].update(call_id='other'))
 reject('unknown_version',lambda x:x['request'].update(contract_version='2.0.0'))
 reject('extra_field',lambda x:x['author_output']['data'].update(ready=True))
 reject('needs_user_without_question',lambda x:x['author_output'].update(status='needs_user',questions=[]))
 reject('completed_with_issues',lambda x:x['author_output'].update(status='completed'))
 for hint in ['aftercare-evidence','aftercare-interact']:
  reject('closed_'+hint,lambda x,hint=hint:x['author_output']['data']['next_steps'].append({'intent':'准备申请','reason':'已选','required_evidence':[],'next_skill_hint':hint}))
 layout=copy.deepcopy(f);layout['host']['page_current']=False
 v=check(layout['request'],layout['author_output'],layout['host']);assert v['choice_valid'] and not v['page_current']
 report['invariants'].append({'case':'layout_only_preserves_choice','result':v})
 for mode in ['self','guided','auto']:
  x=copy.deepcopy(f);x['request']['mode']=mode;x['host']['mode']=mode;x['host']['registry']['snapshot-demo']['data']['mode']=mode
  assert check(x['request'],x['author_output'],x['host'])['submission_authorized'] is False
  report['invariants'].append({'case':mode,'result':'no_execution_authority'})
 before=copy.deepcopy(f);assert check(f['request'],f['author_output'],f['host'])==check(f['request'],f['author_output'],f['host']) and f==before
 downstream=read('examples/downstream-structural-only.json')
 validate('aftercare-evidenceRequest',downstream['evidence_request']);validate('aftercare-interactRequest',downstream['interact_request'])
 report['downstream']='two actual central request definitions validated; no downstream implementation invoked'
 if integration:
  upstream=Path(paths['intake']);sys.path.insert(0,str(upstream/'local_host'))
  demo=load('intake_demo',upstream/'local_host/demo.py')
  with tempfile.TemporaryDirectory() as td:trace=demo.scenario(Path(td)/'synthetic.sqlite')
  try:validate('TaskIntent',trace['completed']['data'])
  except ValidationError:incompatible=True
  else:incompatible=False
  assert incompatible
  order=Path(paths['order']);oc=load('actual_order_checks',order/'tests/selection_checks.py')
  of=json.loads((order/'tests/selection-positive-fixture.json').read_text(encoding='utf-8-sig'))
  ov=oc.check(of['request'],of['result'],of['host']);assert ov['selection_valid'] and not ov['remedy_handoff']
  # Actual order output consumed unchanged as remedy's OrderSelection reference body.
  x=copy.deepcopy(f);x['host']['registry']['order-demo']['data']=copy.deepcopy(of['result']['data'])
  rv=check(x['request'],x['author_output'],x['host']);assert not rv['formal_preparation_allowed']
  report['integration']={'status':'partial_actual_code_executed','intake_local_demo_completed':trace['completed']['status'],'intake_v2_rejected_without_projection':incompatible,'actual_order_checker':ov,'order_output_to_remedy_checker':rv,'model_calls':False,'full_positive_chain':'not_run; contracts incompatible','platform_evidence_interact_runtime':'not_implemented_here'}
 (ROOT/'tests/results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Schema cases:',len(report['schema']),'invariant checks:',len(report['invariants']),'integration:',report['integration']['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--integration',action='store_true');main(p.parse_args().integration)
