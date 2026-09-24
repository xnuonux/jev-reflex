"""Descriptive paired-workflow comparison. Never infers ground truth from Jev."""
import math
import re
from .reflex import identifier, require

FIELDS = {'case_id','input_sha256','correct','important_missed','abstained',
          'duration_ms','cost_microusd','input_tokens','output_tokens'}


def compare(data):
    require(type(data) is dict and set(data)=={'schema','synthetic','baseline','candidate'}, 'evaluation-fields')
    require(data['schema']=='jev-reflex-paired/v1' and type(data['synthetic']) is bool, 'evaluation-schema')
    runs=[]
    for lane in ('baseline','candidate'):
        rows=data[lane]
        require(type(rows) is list and 1 <= len(rows) <= 10000, 'evaluation-population')
        indexed={}
        for row in rows:
            require(type(row) is dict and set(row)==FIELDS, 'evaluation-row')
            key=identifier(row['case_id'])
            require(key not in indexed, 'evaluation-duplicate')
            require(type(row['input_sha256']) is str and re.fullmatch('[a-f0-9]{64}',row['input_sha256']) is not None,'evaluation-digest')
            for field in ('correct','important_missed','abstained'):
                require(row[field] is None or type(row[field]) is bool, 'evaluation-bool')
            for field in ('duration_ms','cost_microusd','input_tokens','output_tokens'):
                value=row[field]
                require(value is None or (type(value) in (float,int) and 0 <= value <= 1e15 and math.isfinite(value)),'evaluation-number')
                if field != 'duration_ms':
                    require(value is None or type(value) is int,'evaluation-integer')
            indexed[key]=row
        runs.append(indexed)
    baseline,candidate=runs
    require(set(baseline)==set(candidate),'evaluation-unpaired')
    require(all(baseline[k]['input_sha256']==candidate[k]['input_sha256'] for k in baseline),'evaluation-input-mismatch')
    metrics={}
    for field in ('correct','important_missed','abstained','duration_ms','cost_microusd','input_tokens','output_tokens'):
        pairs=[(baseline[k][field],candidate[k][field]) for k in baseline
               if baseline[k][field] is not None and candidate[k][field] is not None]
        metrics[field]=dict(paired_known=len(pairs),paired_unknown=len(baseline)-len(pairs),
                            baseline_mean=sum(a for a,b in pairs)/len(pairs) if pairs else None,
                            candidate_mean=sum(b for a,b in pairs)/len(pairs) if pairs else None,
                            candidate_minus_baseline_mean=sum(b-a for a,b in pairs)/len(pairs) if pairs else None)
    return dict(schema='jev-reflex-comparison/v1',synthetic=data['synthetic'],cases=len(baseline),metrics=metrics,
                evidence='caller-supplied paired observations', independent_verification=False,
                source_bytes_verified=False, synthetic_label_source='caller',
                causal_claim=False, estimated_dollar_savings=None)
