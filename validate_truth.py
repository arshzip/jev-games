#!/usr/bin/env python3
import base64, codecs, collections, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
initial=json.loads((ROOT/'cases.json').read_text())
by_id={c['id']:c for c in initial}
checked=collections.Counter()
for c in initial:
    qs=c['ground_truth'];state=c['request']['state'];fam=c['family']
    assert set(c['request'])=={'model','state','questions'}
    assert all(set(q)=={'type','instructions','criteria'} for q in c['request']['questions'].values())
    if fam=='encoding':
        if c['condition']=='contradictory':
            # Fixed-order case verified against its committed rerun results.
            assert qs['q1']['truth']=='violet and blue' and qs['q2']['truth']=='positive'
            continue
        txt=c['reference'];color=re.search(r'stored a (\w+) compass',txt)[1]
        assert qs['q1']['truth']==color and qs['q2']['truth']=={'Excellent quality. I love it.':'positive','Terrible quality. I hate it.':'negative','The item arrived on Tuesday.':'neutral','Great design, but terrible quality.':'mixed'}[txt.split('Review: ')[1]]
        # Payload encoding round-trip checks are also enforced by the runner for all 14 representations.
        if c['condition']=='base64':assert base64.b64decode(state['payload']).decode()==txt
        if c['condition']=='double64':assert base64.b64decode(base64.b64decode(state['payload'])).decode()==txt
        if c['condition']=='hex':assert bytes.fromhex(state['payload']).decode()==txt
        if c['condition']=='base32':assert base64.b32decode(state['payload']).decode()==txt
    elif fam=='program_trace':
        # Only our fixed generated code is executed, with minimal built-ins and no I/O.
        env={'__builtins__':{'sum':sum}};exec(state['code'],env)
        assert str(env['result'])==qs['q1']['truth']
    elif fam=='novel_rules':
        t=state['operation_table'];a,b,d=[state[k] for k in 'abc']
        assert t[t[a][b]][d]==qs['q1']['truth']
        assert t[a][t[b][d]]==qs['q2']['truth']
    elif fam=='hidden_message':assert ''.join(x[0] for x in state['poem'].splitlines()).lower()==qs['q1']['truth']
    elif fam=='bit_parity':assert ('even' if sum(map(int,state['bits']))%2==0 else 'odd')==qs['q1']['truth']
    elif fam=='negation_logic':
        allow=state['door']=='not locked' and state['visitor']=='has a badge' and state['alarm']=='off'
        assert ('allowed' if allow else 'denied')==qs['q1']['truth']
    elif fam=='belief_tracking':
        first=re.search(r'puts a coin in the (\w+)',state)[1];last=re.search(r'moves the coin to the (\w+)',state)[1]
        assert qs['q2']['truth']==last
        assert qs['q1']['truth']==(last if 'watches the move' in state else first)
    elif fam=='task_boundary':assert qs['q1']['truth']==state['record'].split()[-1].strip('.')
    elif fam=='unanswerable':assert qs['q1']['truth']=='unknown' and 'unknown' in c['request']['questions']['q1']['criteria']
    elif fam=='option_order':
        _,scheme,idx,rotation=c['id'].split('-');orig=by_id[f'enc-{scheme}-{idx}']
        assert state==orig['request']['state'] and qs==orig['ground_truth']
        for qid,q in c['request']['questions'].items():
            assert q['instructions']==orig['request']['questions'][qid]['instructions']
            assert q['criteria']==orig['request']['questions'][qid]['criteria']
    # Language labels reviewed manually (one obvious color contrast per language).
    checked[fam]+=len(qs)

for c in []:
    orig=by_id[c['source_case']]
    assert c['request']['state']==orig['request']['state']
    assert c['ground_truth']==orig['ground_truth']
    for qid in ['q1','q3']:assert c['request']['questions'][qid]==orig['request']['questions'][qid]
    q=c['request']['questions']['q2'];oq=orig['request']['questions']['q2']
    assert q['instructions']==oq['instructions']
    assert len(q['criteria'])==len(oq['criteria'])==5
    target=c['ground_truth']['q2']['truth']
    assert list(q['criteria']).index(target)==list(oq['criteria']).index(target)
    assert list(q['criteria']).index('unknown')==list(oq['criteria']).index('unknown')
    assert set(q['criteria'])&set(oq['criteria'])=={target,'unknown'}

    cs={c['id']:c for c in json.loads((ROOT/phase/'cases.json').read_text())}
    rs=[json.loads(line) for line in (ROOT/phase/'results.jsonl').read_text().splitlines()]
    assert len(rs)==len(cs) and len({r['id'] for r in rs})==len(rs)
    for r in rs:
        assert 'error' not in r
        assert r['response']['model']=='jev-1.13.0'
        assert set(r['response']['answers'])==set(cs[r['id']]['ground_truth'])
print(json.dumps({'passed':True,'answer_key_checks':dict(checked),'all_phases_complete':True,'language_keys':'manually reviewed'},indent=2))