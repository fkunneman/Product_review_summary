
import sys
import json
from collections import defaultdict

in_file = sys.argv[1] # frogged json sentences
in_subj_list = sys.argv[2] # from duoman subjectivity lexicon
out_file = sys.argv[3] # [describe output]
json_out = sys.argv[4]

############## Helpers ###############

def extract_pos(word):
    return word['pos'].split('(')[0]

def check_subjectivity(phrase, subj):
    subjective = list(set([word['word'].lower() for word in phrase if word['word'].lower() in subj] + [word['lemma'].lower() for word in phrase if word['lemma'].lower() in subj]))
    return subjective

def score_polarity(subjective_word,subj_pol):
    try:
        pol = subj_pol[subjective_word]
    except:
        pol = '+/-'
    return pol

def assess_phrase(phrase, subj, subj_pol):
    if len(phrase) == 1: # no phrase
        return False
    poss = [extract_pos(w) for w in phrase]
    if poss.count('ADJ') == 0: # pro or con should have at least one adjective
        return False
    if extract_pos(phrase[-1]) == 'VZ': # pro or con can not end with preposition
        return False
    if extract_pos(phrase[-1]) == 'WW': # pro or con can not end with particular variant of verb
        if phrase[-1]['pos'][:5] == 'WW(pv':
            return False
    if extract_pos(phrase[0]) == 'WW': # pro or con can not start with particular variant of verb
        if phrase[0]['pos'][:5] == 'WW(pv':
            return False
    if extract_pos(phrase[-1]) == 'VG': # pro or con can not end with conjunction
        return False
    subjective_words = check_subjectivity(phrase,subj)
    if len(subjective_words) > 0: # pro or con should contain a subjective word
        # decide polarity (pro or con)
        polarities = [score_polarity(sw,subj_pol) for sw in subjective_words]
        if len(list(set(polarities))) == 1:
            polarity = polarities[0]
        else:
            sorted_polarity_counts = sorted([[x,polarities.count(x)] for x in list(set(polarities))],key = lambda k : k[1],reverse=True)
            if sorted_polarity_counts[0][1] > sorted_polarity_counts[1][1]:
                polarity = sorted_polarity_counts[0][0]
            else:
                if len(sorted_polarity_counts) == 2:
                    if '+/-' in polarities:
                        polarity = [x for x in polarities if x != '+/-'][0]
                    else: # '+' and '-'
                        polarity = '-'
                else: # all three are in there
                    if sorted_polarity_counts[0][1] > sorted_polarity_counts[2][1]:
                        if '+/-' in [x[0] for x in sorted_polarity_counts[:2]]:
                            polarity = [x[0] for x in sorted_polarity_counts[:2] if x[0] != '+/-'][0]
                        else: # '+' and '-'
                            polarity = '-'
                    else: # same number of words with polarity
                        polarity = '-'
        return([subjective_words,polarities,polarity]) # return information
    else:
        return False

############## Preparations ###############

# read in subjectivity lexicon
subj_polarity = {}
with open(in_subj_list,'r',encoding='utf-8') as file_in:
    subj_assessments = file_in.read().strip().split('\n')

# generate subjective word-polarity dictionary
for line in subj_assessments:
    tokens = line.split('\t')
    word_pos = tokens[0].split()
    word = word_pos[0]
    pos = word_pos[1]
    assessments = tokens[1:]
    polarity = list(set([assessment[0] for assessment in assessments]))
    if len(polarity) == 1:
        pol = polarity[0]
    else:
        if '-' in polarity and '+' in polarity:
            # check if one of the two is given double
            if '++' in assessments and '-' in assessments:
                pol = '+'
            elif '--' in assessments and '+' in assessments:
                pol = '-'
            else:
                continue
    subj_polarity[word] = pol
subjectivities = subj_polarity.keys()

############## Main script ###############

# initiate lists to write the output to
output = []
output_full = []

# read in reviews (as frogged sentences in json format)
with open(infile,'r',encoding='utf-8') as file_in:
    reviews = json.loads(file_in.read())

matches = [] # to save all matching patterns for this review
for review in reviews: # for each review
    for sentence in review: # for each sentence
        ph = False # to check whether a phrase matching a pattern is being parsed
        review_index = sentence[0]['review_id']
        sentext = ' '.join([token['word'] for token in sentence])
        for i,word in enumerate(sentence): # for each word in the sentence
            if extract_pos(word) == 'ADJ': # might match pattern for subject phrase
                if not ph: # start phrase
                    phrase = [word]
                    ph = True
                else:
                    if extract_pos(phrase[-1]) == 'N' or extract_pos(phrase[-1]) == 'ADJ' or phrase[-1]['phrase'][1:] == '-VP' or phrase[-1]['phrase'] == 'B-NP' or extract_pos(phrase[-1]) == 'VZ': # ADJ can be added to phrase
                        phrase.append(word)
                    else:
                        polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                        if polarity:
                            matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                        phrase = [word]
            elif extract_pos(word) == 'N': # might match pattern for subject phrase
                if not ph: # start phrase
                    phrase = [word]
                    ph = True
                else:
                    if extract_pos(phrase[-1]) == 'N' or extract_pos(phrase[-1]) == 'ADJ' or extract_pos(phrase[-1]) == 'VZ' or phrase[-1]['phrase'] == 'B-NP' or phrase[-1]['phrase'] == 'I-ADJP': # N can be added to phrase
                        phrase.append(word)
                    else:
                        polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                        if polarity:
                            matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                        phrase = [word]               
            elif word['phrase'] == 'B-ADVP':
                if not ph:
                    phrase = [word]
                    ph = True
                else:
                    polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                    if polarity:
                        matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                    phrase = [word]                    
            elif word['phrase'] == 'B-NP':
                if not ph:
                    phrase = [word]
                    ph = True
                else:
                    if extract_pos(phrase[-1]) == 'VZ' or phrase[-1]['phrase'] == 'B-ADVP':
                        phrase.append(word)
                    else:
                        polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                        if polarity:
                            matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                        phrase = [word]                    
            elif word['phrase'] == 'I-NP':
                if ph:
                    phrase.append(word)
            elif word['phrase'] == 'I-ADJP':
                if ph:
                    if extract_pos(phrase[-1]) == 'ADJ':
                        phrase.append(word)
                    else:
                        polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                        if polarity:
                            matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                        ph = False                       
                        phrase = []
            elif extract_pos(word) == 'VZ': # might continue pattern for subject phrase
                if ph:
                    if extract_pos(phrase[-1]) == 'ADJ': # fits pattern
                        phrase.append(word)
                    else:
                        polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                        if polarity:
                            matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                        ph = False                       
                        phrase = []
                else:
                    phrase = [word]
                    ph = True
            elif word['phrase'][1:] == '-VP': # might continue pattern for subject phrase
                if word['phrase'] == 'B-VP':
                    if not ph:
                        phrase = [word]
                        ph = True
                    else:
                        if extract_pos(phrase[-1]) == 'ADJ' or phrase[-1]['phrase'] == 'B-NP' or extract_pos(phrase[-1]) == 'N' or phrase[-1]['phrase'] == 'B-ADVP': # fits pattern
                            phrase.append(word)
                        else:
                            polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                            if polarity:
                                matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                            ph = False
                            phrase = []
                else: 
                    if ph:
                        if phrase[-1]['phrase'][1:] == '-VP':
                            phrase.append(word)
                        else:
                            polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                            if polarity:
                                matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                            ph = False
                            phrase = []
            else:
                if ph:
                    polarity = assess_phrase(phrase,subjectivities,subj_polarity)
                    if polarity:
                        matches.append([review_index,sentext,' '.join([x['word'] for x in phrase]),' '.join([extract_pos(x) for x in phrase]),' '.join([x['phrase'] for x in phrase])] + polarity)
                    ph = False
                    phrase = []
                else:
                    phrase = []

############## Write output ###############            

# Simple overview of output as tab-separated data
with open(outfile,'w',encoding='utf-8') as out:
    out.write('\n'.join(['\t'.join([str(token) for token in match]) for match in matches]))

# Full overview in json
review_id_out = {}
for match in matches:
    review_id = str(match[0])
    if review_id not in review_id_out.keys():
        review_id_out[review_id] = {'text':match[1],'pattern_pros':[],'pattern_cons':[]}
    if match[-1] == '+':
        review_id_out[review_id]['pattern_pros'].append(match[2])
    else:
        review_id_out[review_id]['pattern_cons'].append(match[2])
patterns_json_out = []
for review_id in review_id_out.keys():
    review_dict = review_id_out[review_id]
    review_dict['index'] = review_id
    patterns_json_out.append(review_dict)

with open(json_out,'w',encoding='utf-8') as out:
    json.dump(patterns_json_out,out)
