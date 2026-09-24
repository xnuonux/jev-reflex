"""Offline labelled decision evaluation. No threshold tuning or model calls."""
from .reflex import identifier, probability, require, result


def report(data):
    require(type(data) is dict and set(data) == {'schema','labels','cases'}, 'shadow-fields')
    require(data['schema'] == 'shadow/v1', 'shadow-schema')
    labels, cases = data['labels'], data['cases']
    require(type(labels) is list and 2 <= len(labels) <= 255, 'shadow-labels')
    for label in labels:
        identifier(label)
    require(len(set(labels)) == len(labels), 'shadow-labels')
    require(type(cases) is list and 1 <= len(cases) <= 10000, 'shadow-cases')
    routes, seen = {}, set()
    for row in cases:
        require(type(row) is dict and set(row) == {'id','route','truth','prediction','confidence'}, 'shadow-case')
        name, route = identifier(row['id']), identifier(row['route'])
        require(name not in seen, 'shadow-duplicate')
        seen.add(name)
        for key in ('truth','prediction'):
            require(row[key] is None or (type(row[key]) is str and row[key] in labels), 'shadow-label')
        if row['confidence'] is not None:
            probability(row['confidence'])
        routes.setdefault(route, []).append(row)
    return result('ok', schema='shadow-report/v1', routes={k:_summary(v,labels) for k,v in routes.items()},
                  evidence='caller-labelled-observations', calibrated_correctness_established=False,
                  automatic_threshold_change=False, provider_calls=0)


def _summary(rows, labels):
    known = [r for r in rows if r['truth'] is not None]
    selected = [r for r in known if r['prediction'] is not None]
    matrix = {a:{b:0 for b in labels} for a in labels}
    for row in selected:
        matrix[row['truth']][row['prediction']] += 1
    per_class = {}
    for label in labels:
        true_count = sum(r['truth'] == label for r in known)
        predicted_count = sum(r['prediction'] == label for r in selected)
        correct = matrix[label][label]
        per_class[label] = dict(support=true_count, predicted=predicted_count,
                               precision=correct/predicted_count if predicted_count else None,
                               recall=correct/true_count if true_count else None,
                               abstentions=sum(r['truth']==label and r['prediction'] is None for r in known))
    bins = []
    for low, high in ((0,.5),(.5,.75),(.75,.9),(.9,1.0)):
        members = [r for r in selected if r['confidence'] is not None and low <= r['confidence'] and
                   (r['confidence'] < high or high == 1.0)]
        bins.append(dict(lower_inclusive=low,upper=high,upper_inclusive=high==1.0,count=len(members),
                         mean_confidence=sum(r['confidence'] for r in members)/len(members) if members else None,
                         accuracy=sum(r['truth']==r['prediction'] for r in members)/len(members) if members else None))
    return dict(total=len(rows),known_truth=len(known),unknown_truth=len(rows)-len(known),
                scored_predictions=len(selected),predictions_total=sum(r['prediction'] is not None for r in rows),
                unknown_truth_predictions=sum(r['truth'] is None and r['prediction'] is not None for r in rows),
                abstentions=sum(r['prediction'] is None for r in rows),
                coverage=len(selected)/len(known) if known else None,
                selective_accuracy=sum(r['truth']==r['prediction'] for r in selected)/len(selected) if selected else None,
                confusion=matrix,per_class=per_class,confidence_bins=bins,
                unknown_confidence=sum(r['confidence'] is None for r in selected))
