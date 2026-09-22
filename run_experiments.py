#!/usr/bin/env python3
"""jev-games suite — executes the pinned cases in cases.json (the games covered in
the blog post, and nothing else). Standard-library only; the API key is read from
the environment and never written to disk.
Run: TYPESAFE_API_KEY=... python3 run_experiments.py   (API calls incur usage)
Results are resumed by case id; move results.jsonl and manifest.json aside for a
fresh run. cases.json is the single source of truth: exact requests (only the
`request` object was transmitted), local-only expected answers, references, and
fixed option orders. The access-tag question and tag material were removed from
the encoding records; the missing-information prompts never mention `unknown`."""
import concurrent.futures, datetime, hashlib, json, os, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT/'cases.json').read_text())

# Verify structural integrity before making any paid call.
assert len({c['id'] for c in CASES})==len(CASES)
for case in CASES:
    for qid,g in case['ground_truth'].items():
        assert g['truth'] in case['request']['questions'][qid]['criteria']
    if case['family']=='unanswerable':
        # The whole point of these cases: no hint that unknown is an option.
        assert 'unknown' not in json.dumps(case['request']['questions']).replace('"unknown": null',''), 'hint leaked into prompt'
MANIFEST={'requested_model':'jev-1.13.0','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'planned_cases':len(CASES),'planned_questions':sum(len(c['ground_truth']) for c in CASES),'protocol':'One independent state per request. Related questions are batched. Ground truth and decoded references are not sent. Fixed option orders (pinned from the historical run). No model decoder or external tools provided. No prompt suggests picking unknown.','suite_sha256':hashlib.sha256((ROOT/'cases.json').read_bytes()).hexdigest()}

def api_call(case):
    key=os.environ.get('TYPESAFE_API_KEY')
    if not key: raise RuntimeError('Export TYPESAFE_API_KEY before running. The key is never saved.')
    attempts=[]; start=time.perf_counter()
    for attempt in range(3):
        t=time.perf_counter()
        try:
            req=urllib.request.Request('https://api.typesafe.ai/v1/systemone',data=json.dumps(case['request']).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=35) as r: response=json.load(r)
            attempts.append({'status':200,'ms':round((time.perf_counter()-t)*1000)})
            assert set(response['answers'])==set(case['ground_truth']), 'Missing answer'
            for qid,a in response['answers'].items():
                assert a['type']=='choice' and a['choice'] in case['request']['questions'][qid]['criteria']
                ps=a['probabilities']; assert set(ps)==set(case['request']['questions'][qid]['criteria'])
                assert all(0<=p<=1 for p in ps.values()) and abs(sum(ps.values())-1)<0.025
                assert 0<=a['confidence']<=1
            return {'id':case['id'],'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_ms':round((time.perf_counter()-start)*1000),'attempts':attempts,'response':response}
        except Exception as e:
            status=getattr(e,'code',None)
            attempts.append({'status':status,'error':type(e).__name__,'ms':round((time.perf_counter()-t)*1000)})
            if isinstance(e,urllib.error.HTTPError) and status not in [429,500,502,503,504,529]: break
            if attempt<2:
                retry=e.headers.get('retry-after','0') if isinstance(e,urllib.error.HTTPError) else '0'
                try: delay=float(retry)
                except ValueError: delay=0
                time.sleep(min(30,max(delay,2**attempt)))
    return {'id':case['id'],'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_ms':round((time.perf_counter()-start)*1000),'attempts':attempts,'error':'Request or response validation failed; see attempt metadata.'}

def main():
    out=ROOT/'results.jsonl'; completed={}
    if out.exists():
        for line in out.read_text().splitlines():
            row=json.loads(line); completed[row['id']]=row
    if out.exists() and (ROOT/'manifest.json').exists():
        prior=json.loads((ROOT/'manifest.json').read_text())
        assert prior['suite_sha256']==MANIFEST['suite_sha256'], 'Suite changed; move results.jsonl and manifest.json aside first.'
        MANIFEST['created_at']=prior['created_at']
    (ROOT/'manifest.json').write_text(json.dumps(MANIFEST,indent=2))
    pending=[c for c in CASES if c['id'] not in completed]
    print(f'{len(CASES)} requests / {MANIFEST["planned_questions"]} judgments; {len(pending)} pending. Concurrency: 6.',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool, out.open('a') as f:
        futures={pool.submit(api_call,c):c for c in pending}
        for future in concurrent.futures.as_completed(futures):
            row=future.result(); f.write(json.dumps(row,ensure_ascii=False)+'\n'); f.flush(); completed[row['id']]=row
            print(f'[{len(completed)}/{len(CASES)}] {row["id"]}: {"ERROR" if "error" in row else "ok"} {row["elapsed_ms"]}ms',flush=True)
    print('Finished. Errors:',sum('error' in r for r in completed.values()),flush=True)

if __name__=='__main__': main()
