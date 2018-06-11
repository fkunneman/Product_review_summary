
import sys
import json
import re
import difflib
import numpy
from collections import defaultdict
import math

trainfile = sys.argv[1] # train, dev and test formatted as json file, as a list of reviews ({'pros':[], 'cons':[], 'id':str, 'txt':str})
devfile = sys.argv[2]
testfile = sys.argv[3]
predictions_out = sys.argv[4]

def summary_overlap(s1,s2):
    if set(s1.split()) & set(s2.split()):
        return True
    else:
        return False

def resolve_overlap(sorted_summaries):
    non_overlapping = [sorted_summaries[0]]
    for summary2 in sorted_summaries[1:]:
        overlap = False
        for summary1 in non_overlapping:
            if summary_overlap(summary1,summary2):
                overlap = True
                break
        if not overlap:
            non_overlapping.append(summary2)
    return non_overlapping

def get_overlap(s1, s2):
    s = difflib.SequenceMatcher(None, s1, s2)
    pos_a, pos_b, size = s.find_longest_match(0, len(s1), 0, len(s2))
    return s1[pos_a:pos_a+size]

def extract_ngrams(tokens,n):
    ngrams = list(zip(*[tokens[i:] for i in range(n)]))
    ngrams_string = [' '.join(ngram) for ngram in ngrams]
    return ngrams_string

def predict_summary(text,summary_dict,threshold):
    predictions = []
    for summary, ngrams in summary_dict.items():
        selections = []
        for ngram in ngrams:
            try:
                if re.search(ngram,text):
                    selections.append([ngram,len(ngram)])
            except:
                continue
        if len(selections) > 0:
            max_len = max([x[1] for x in selections])
            if max_len/len(summary) > threshold:
                final_selections = [x[0] for x in selections if x[1] == max_len]
                predictions.append([summary,final_selections,max_len/len(summary)])
    return predictions

def score_overlap(str1,str2):
    return len(get_overlap(str1, str2)) / len(str1)

def return_best_overlap(prediction,gold_standard):
    best = 0
    best_gold_standard = False
    prediction_str = prediction[0]
    for ref in gold_standard:
        try:
            overlap = score_overlap(ref,prediction_str)
            if overlap > best:
                best = overlap
                best_gold_standard = ref
        except:
            continue
    return best, best_gold_standard

def return_overlap(gold_standard,predicted):
    overlaps = []
    for prediction in predicted:
        best_overlap, best_gold_standard = return_best_overlap(prediction,gold_standard)
        overlaps.append([prediction,best_gold_standard,best_overlap])
    return overlaps

def score_overlaps(gold_standard,overlaps):
    try:
        avg_best_overlap = numpy.mean([x[2] for x in overlaps])
        recall = len([gs for gs in gold_standard if gs in [x[1] for x in overlaps]]) / len(gold_standard)
        return avg_best_overlap, recall
    except:
        return False, False
        
# open train
print('Reading in train...')
pros_ngrams = {}
cons_ngrams = {}
with open(trainfile,'r',encoding='utf-8') as file_in:
    train = json.loads(file_in.read())
    all_trainpros = sum([r['pros'] for r in train],[])
    all_traincons = sum([r['cons'] for r in train],[])
    for p in all_trainpros:
        tokens = p.split()
        pros_ngrams[p] = sum([extract_ngrams(tokens,token_length) for token_length in range(len(tokens))],[])
    for c in all_traincons:
        tokens = c.split()
        cons_ngrams[c] = sum([extract_ngrams(tokens,token_length) for token_length in range(len(tokens))],[])
                                          
# open dev
print('Processing dev...')
thresholds = [0.4,0.5,0.6,0.7]
threshold_overlaps = defaultdict(list)
with open(devfile,'r',encoding='utf-8') as file_in:
    dev = json.loads(file_in.read())
    for i,r in enumerate(dev):
        for threshold in thresholds:
            predicted_pros = predict_summary(r['txt'],pros_ngrams,threshold)
            predicted_cons = predict_summary(r['txt'],cons_ngrams,threshold)
            gold_standard_pros = r['pros']
            gold_standard_cons = r['cons']
            overlaps = return_overlap(gold_standard_pros,predicted_pros) + return_overlap(gold_standard_cons,predicted_cons)
            avg_overlap, recall = score_overlaps(gold_standard_pros + gold_standard_cons,overlaps)
            if not avg_overlap == False and not math.isnan(avg_overlap):
                threshold_overlaps[threshold].append([avg_overlap,recall])

highest = 0
best_threshold = False
for threshold in thresholds:
    # performance = numpy.mean([numpy.mean([x[0] for x in threshold_overlaps[threshold]]),numpy.mean([x[1] for x in threshold_overlaps[threshold]])])
    if len(threshold_overlaps[threshold])/len(dev) > 0.75:
        performance = numpy.mean([x[0] for x in threshold_overlaps[threshold]])
        if performance > highest:
            highest = performance
            best_threshold = threshold
print('Completed development. Best threshold:',best_threshold,'perfromance:',highest)

# open test
print('Processing test...')
out_predictions = []
with open(testfile,'r',encoding='utf-8') as file_in:
    test = json.loads(file_in.read())
    for i,r in enumerate(test):
        predicted_pros = predict_summary(r['txt'],pros_ngrams,best_threshold)
        predicted_cons = predict_summary(r['txt'],cons_ngrams,best_threshold)
        sorted_predicted_pros = sorted(predicted_pros,key = lambda k : k[2],reverse = True)
        sorted_predicted_cons = sorted(predicted_cons,key = lambda k : k[2],reverse = True)
        r_out = r
        if len(sorted_predicted_pros) > 0:
            if len(sorted_predicted_pros) > 1:
                predicted_pros_no_overlap = resolve_overlap([x[0] for x in sorted_predicted_pros])
            else:
                predicted_pros_no_overlap = sorted_predicted_pros[0][0]
            r_out['baseline_pros'] = predicted_pros_no_overlap
        else:
            r_out['baseline_pros'] = []
        if len(sorted_predicted_cons) > 0:
            if len(sorted_predicted_cons) > 1:
                predicted_cons_no_overlap = resolve_overlap([x[0] for x in sorted_predicted_cons])
            else:
                predicted_cons_no_overlap = sorted_predicted_cons[0][0]
            r_out['baseline_cons'] = predicted_cons_no_overlap
        else:
            r_out['baseline_cons'] = []
        out_predictions.append(r_out)

# write to file
print('Writing to file...')
with open(predictions_out,'w',encoding='utf-8') as out:
    json.dump(out_predictions,out)
