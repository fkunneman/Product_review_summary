
import sys
import json
import os
from collections import defaultdict
from copy import deepcopy

from fuzzywuzzy import fuzz
import numpy

import linewriter

system_output = sys.argv[1] # system output in .json
gold_standard = sys.argv[2] # human gold standard (.json)
threshold = int(sys.argv[3]) # between 0 and 100
proskey = sys.argv[4] # to extract pros from .json system output
conskey = sys.argv[5] # to extract cons from .json system output
eval_out = sys.argv[6] # .json file
aggr_eval_out = sys.argv[7] # .csv file

review_predictions = defaultdict(list)
review_txt = {}
review_pros = {}
review_cons = {}

def return_distance(x,y):
    return fuzz.token_set_ratio(x,y)

def return_distancetable(sources,targets):
    distancetable = []
    for source in sources:
        for target in targets:
            distancetable.append([source,target,return_distance(source,target)])
    return distancetable

def align_sentences(sources,targets):
    distancetable = return_distancetable(sources,targets)
    sentences_aligned = []
    sources_aligned = []
    targets_aligned = []
    for distance in sorted(distancetable,key = lambda k : k[2],reverse=True):
        if distance[0] not in sources_aligned and distance[1] not in targets_aligned:
            sentences_aligned.append(distance)
            sources_aligned.append(distance[0])
            targets_aligned.append(distance[1])
    sources_extra = [source for source in sources if source not in sources_aligned]
    targets_extra = [target for target in targets if target not in targets_aligned]
    return sentences_aligned, sources_extra, targets_extra               

def evaluate_alignment(sentences_aligned,sources_extra,targets_extra,threshold):
    if len(sentences_aligned) > 0:
        scores = [x[2] for x in sentences_aligned]
        avg = numpy.mean(scores)
        best = max(scores)
        thr = [x for x in sentences_aligned if x[2] > threshold]
        under_thr = [x for x in sentences_aligned if x[2] <= threshold]
    else:
        scores = []
        avg = 0
        best = 0
        thr = []
        under_thr = []
    tp = len(thr)
    fn = len(under_thr) + len(targets_extra)
    fp = len(under_thr) + len(sources_extra)
    try:
        pr = tp/(tp+fp)
    except:
        pr = 0
    try:
        re = tp/(tp+fn)
    except:
        re = 0
    return avg, best, tp, fn, fp, pr, re

def match_empty(sources,targets):
    sources_empty = []
    targets_empty = []
    if len(sources) == 0:
        sources_empty.append('-')
    else:
        for source in sources:
            if source in ['geen','nog niet gevonden','nog niet ontdekt','nog niet ontdekt (apparaat pas aangeschaft)','nog geen gevonden','-']: 
                sources_empty.append(source)
    if len(targets) == 0:
        targets_empty.append('-')
    else:
        for target in targets:
            if target in ['geen','geen geen','nog niet gevonden','nog niet ontdekt','nog niet ontdekt (apparaat pas aangeschaft)','nog geen gevonden','-']:
                targets_empty.append(target)
    aligned = []
    sources_extra = []
    targets_extra = []
    if len(sources_empty) > 0 and len(targets_empty) > 0:
        me = [1,0,0]
        for i,source in enumerate(sources_empty):
            try:
                aligned.append([source,targets_empty[i],100])
            except:
                break
    elif len(sources_empty) > 0 and len(targets_empty) == 0:
        me = [0,0,1]
        sources_extra.extend(sources_empty)
    elif len(sources_empty) == 0 and len(targets_empty) > 0:
        me = [0,1,0]
        targets_extra.append(targets_empty)
    else:
        me = [0,0,0]
    new_sources = deepcopy(sources)
    if len(new_sources) > 0:
        for x in sources_empty:
            new_sources.remove(x)
    new_targets = deepcopy(targets)
    if len(new_targets) > 0:
        for x in targets_empty:
            new_targets.remove(x)
    return me, new_sources, new_targets, aligned, sources_extra, targets_extra
        
# read in system output
with open(system_output,'r',encoding='utf-8') as file_in:
    predictions = json.loads(file_in.read())
predictiondict = {}
for pr in predictions:
    predictiondict[int(pr['index'])] = pr
    
# read in gold standard
with open(gold_standard,'r',encoding='utf-8') as file_in:
    targets = json.loads(file_in.read())
targetdict = {}
for ta in targets:
    targetdict[int(ta['index'])] = ta
    
# evaluate performance
all_output = []
all_pr_pros = []
all_pr_cons = []
all_pr_total = []
all_re_pros = []
all_re_cons = []
all_re_total = []
all_f1_pros = []
all_f1_cons = []
all_f1_total = []
num_targets = 0
target_pros = 0
target_cons = 0
predicted_pros = 0
predicted_cons = 0
aligned_pros = 0
aligned_cons = 0
num_predictions = 0
num_aligned = 0
similarities_cons = []
similarities_pros = []

for reviewindex in sorted(predictiondict.keys()):
    print(reviewindex)
    prediction = predictiondict[reviewindex]
    target = targetdict[reviewindex] 
    text = target['txt']
    pr_pros = [x.replace('_',' ').lower() for x in prediction[proskey]] 
    pr_cons = [x.replace('_',' ').lower() for x in prediction[conskey]] 
    pros = [x.lower() for x in target['pros']]
    cons = [x.lower() for x in target['cons']]
    target_pros += len(pros)
    target_cons += len(cons)
    predicted_pros += len(pr_pros)
    predicted_cons += len(pr_cons)
    scores_me_pros, pr_pros_filtered, pros_filtered, empty_aligned_pros, empty_sources_extra_pros, empty_targets_extra_pros = match_empty(pr_pros,pros)
    scores_me_cons, pr_cons_filtered, cons_filtered, empty_aligned_cons, empty_sources_extra_cons, empty_targets_extra_cons = match_empty(pr_cons,cons)
    sentences_aligned_pros,sources_extra_pros,targets_extra_pros = align_sentences(pr_pros_filtered,pros_filtered)
    for sa in sentences_aligned_pros:
        similarities_pros.append(sa[2])
    aligned_pros += len(sentences_aligned_pros)
    scores_pros = evaluate_alignment(sentences_aligned_pros,sources_extra_pros,targets_extra_pros,threshold)
    tp_summed_pros = scores_pros[2] + scores_me_pros[0]
    fn_summed_pros = scores_pros[3] + scores_me_pros[1]
    fp_summed_pros = scores_pros[4] + scores_me_pros[2]
    pr_pros = tp_summed_pros/(tp_summed_pros+fp_summed_pros)
    re_pros = tp_summed_pros/(tp_summed_pros+fn_summed_pros)
    try:
        f1_pros = 2*((pr_pros*re_pros)/(pr_pros+re_pros))
    except:
        f1_pros = 0
    sentences_aligned_cons,sources_extra_cons,targets_extra_cons = align_sentences(pr_cons_filtered,cons_filtered)
    for sa in sentences_aligned_cons:
        similarities_cons.append(sa[2])
    aligned_cons += len(sentences_aligned_cons)
    scores_cons = evaluate_alignment(sentences_aligned_cons,sources_extra_cons,targets_extra_cons,threshold)
    tp_summed_cons = scores_cons[2] + scores_me_cons[0]
    fn_summed_cons = scores_cons[3] + scores_me_cons[1]
    fp_summed_cons = scores_cons[4] + scores_me_cons[2]
    pr_cons = tp_summed_cons/(tp_summed_cons+fp_summed_cons)
    re_cons = tp_summed_cons/(tp_summed_cons+fn_summed_cons)
    try:
        f1_cons = 2*((pr_cons*re_cons)/(pr_cons+re_cons))
    except:
        f1_cons = 0
    tp_total = tp_summed_pros+tp_summed_cons
    fn_total = fn_summed_pros+fn_summed_cons
    fp_total = fp_summed_pros+fp_summed_cons
    pr_total = tp_total/(tp_total+fp_total)
    re_total = tp_total/(tp_total+fn_total)
    try:
        f1_total = 2*((pr_total*re_total)/(pr_total+re_total))
    except:
        f1_total = 0
    review_output = {'index':reviewindex, 'text':text, 'aligned_pros':sentences_aligned_pros+empty_aligned_pros, 'aligned_cons':sentences_aligned_cons+empty_aligned_cons, 'predictions_extra_pros':sources_extra_pros+empty_sources_extra_cons, 'predictions_extra_cons':sources_extra_cons+empty_sources_extra_cons, 'targets_extra_pros':targets_extra_pros+empty_targets_extra_pros, 'targets_extra_cons':targets_extra_cons+empty_targets_extra_cons,'TP pros':tp_summed_pros,'TP cons':tp_summed_cons,'FN pros':fn_summed_pros, 'FN cons':fn_summed_cons, 'FP pros':fp_summed_pros, 'FP cons':fp_summed_cons, 'Precision pros':pr_pros, 'Recall pros':re_pros, 'F-score pros':f1_pros, 'Precision cons':pr_cons, 'Recall cons': re_cons, 'F-score cons':f1_cons, 'TP total':tp_total, 'FP total':fp_total, 'FN total':fn_total, 'Precision total':pr_total, 'Recall total':re_total, 'F-score total':f1_total} 
    all_output.append(review_output)
    all_pr_pros.append(pr_pros)
    all_pr_cons.append(pr_cons)
    all_pr_total.append(pr_total)
    all_re_pros.append(re_pros)
    all_re_cons.append(re_cons)
    all_re_total.append(re_total)
    all_f1_pros.append(f1_pros)
    all_f1_cons.append(f1_cons)
    all_f1_total.append(f1_total)

# write to outfile
with open(eval_out,'w',encoding='utf-8') as out:
    json.dump(all_output,out)
                        
avg_pr_pros = round(numpy.mean(all_pr_pros),2)
mdn_pr_pros = round(numpy.median(all_pr_pros),2)
std_pr_pros = round(numpy.std(all_pr_pros),2)
avg_re_pros = round(numpy.mean(all_re_pros),2)
mdn_re_pros = round(numpy.median(all_re_pros),2)
std_re_pros = round(numpy.std(all_re_pros),2)
avg_f1_pros = round(numpy.mean(all_f1_pros),2)
mdn_f1_pros = round(numpy.median(all_f1_pros),2)
std_f1_pros = round(numpy.std(all_f1_pros),2)
avg_pr_cons = round(numpy.mean(all_pr_cons),2)
mdn_pr_cons = round(numpy.median(all_pr_cons),2)
std_pr_cons = round(numpy.std(all_pr_cons),2)
avg_re_cons = round(numpy.mean(all_re_cons),2)
mdn_re_cons = round(numpy.median(all_re_cons),2)
std_re_cons = round(numpy.std(all_re_cons),2)
avg_f1_cons = round(numpy.mean(all_f1_cons),2)
mdn_f1_cons = round(numpy.median(all_f1_cons),2)
std_f1_cons = round(numpy.std(all_f1_cons),2)
avg_pr_total = round(numpy.mean(all_pr_total),2)
mdn_pr_total = round(numpy.median(all_pr_total),2)
std_pr_total = round(numpy.std(all_pr_total),2)
avg_re_total = round(numpy.mean(all_re_total),2)
mdn_re_total = round(numpy.median(all_re_total),2)
std_re_total = round(numpy.std(all_re_total),2)
avg_f1_total = round(numpy.mean(all_f1_total),2)
mdn_f1_total = round(numpy.median(all_f1_total),2)
std_f1_total = round(numpy.std(all_f1_total),2)

output_scores = [['cat','precision (median)','precision (avg)','precision (std)','recall (median)','recall (avg)','recall (std)','f1 (median)','f1 (avg)','f1 (std)'],['pros',mdn_pr_pros,avg_pr_pros,std_pr_pros,mdn_re_pros,avg_re_pros,std_re_pros,mdn_f1_pros,avg_f1_pros,std_f1_pros],['cons',mdn_pr_cons,avg_pr_cons,std_pr_cons,mdn_re_cons,avg_re_cons,std_re_cons,mdn_f1_cons,avg_f1_cons,std_f1_cons],['total',mdn_pr_total,avg_pr_total,std_pr_total,mdn_re_total,avg_re_total,std_re_total,mdn_f1_total,avg_f1_total,std_f1_total]]
lw = linewriter.Linewriter(output_scores)
lw.write_csv(aggr_eval_out)

print('# predicted pros',predicted_pros)
print('# predicted cons',predicted_cons)
print('# target pos',target_pros)
print('# target cons',target_cons)
print('# aligned pros',aligned_pros)
print('# aligned cons',aligned_cons)
print('avg similarities pros',numpy.mean(similarities_pros))
print('avg similarities cons',numpy.mean(similarities_cons))
