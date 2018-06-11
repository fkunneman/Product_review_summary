
import sys
import json
from collections import defaultdict

infile = sys.argv[1] # Frog postagged sentences in json-format, as list of reviews, where each review is a list of sentences and each sentence is a list of tokens ({'word':str, 'lemma':str, 'pos',str}) 
in_subj_list = sys.argv[2] # from duoman subjectivity lexicon
outfile = sys.argv[3] 
outfile_sentences = sys.argv[4]
subj = int(sys.argv[5])

"""
PREP
parse subjectivity lexicon, describe polarity as positive or negative
"""
subj_polarity = {}
with open(in_subj_list,'r',encoding='utf-8') as file_in:
    subj_assessments = file_in.read().strip().split('\n')

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

#######################

output = []
output_full = []

# read reviews
with open(infile,'r',encoding='utf-8') as file_in:
    reviews = json.loads(file_in.read())

# for each review
for review in reviews:
    ph = False
    ms = []
    # for each sentence
    for sentence in review:
        review_index = sentence[0]['review_id'] # keep track of review
        sentext = ' '.join([token['word'] for token in sentence])
        # for each word in the sentence
        for i,word in enumerate(sentence): 
            m = False
            # check if word is in subjectivity lexicon (match to both lemma and word)
            if subj:
                if word['word'] in subjectivities:
                    m = word['word']
                elif word['lemma'] in subjectivities:
                    m = word['lemma']
            else:
                m = word['word']
            # in case of a match, start looking for syntactic patterns
            if m:
                pos = word['pos'].split('(')[0]
                if pos == 'ADJ' or pos == 'N': # For patterns that start with a noun or adjective/adverb
                    try:
                        pol = subj_polarity[m]
                    except:
                        pol = '+/-'
                    if pos == 'ADJ': # might match pattern for subject phrase --> ADJ, ADJ + N + ..., ADJ + ADJ + ..., ADJ + VZ + ... ADJ + B-VP + ..., 
                        if len(sentence) > i+1: # there is a next word
                            next_word = sentence[i+1]
                            next_word_pos = next_word['pos'].split('(')[0]
                            next_word_phrase = next_word['phrase']
                            if next_word_pos == 'ADJ' or next_word_pos == 'N': # phrase matches postag pattern
                                for subsequent_word in sentence[i+1:]:
                                    subsequent_word_pos = subsequent_word['pos'].split('(')[0]
                                    if subsequent_word_pos == 'ADJ' or subsequent_word_pos == 'N':
                                        if ph: # existing phrase is extended with another word
                                            ms.append(m)
                                            phrase.append(subsequent_word['word'])
                                            poss.append(subsequent_word_pos)
                                        else: # new phrase needs to be generated
                                            phrase = [word['word'],subsequent_word['word']]
                                            poss = [pos,subsequent_word_pos]
                                            ph = True
                                            ms = [m]
                                    else:
                                        break
                            elif next_word_pos == 'VZ':
                                if len(sentence) > i+2:
                                    subsequent_word = sentence[i+2]
                                    subsequent_word_pos = subsequent_word['pos'].split('(')[0]
                                    if subsequent_word_pos == 'N':
                                        if ph: # existing phrase is extended with another word
                                            ms.append(m)
                                            phrase.extend([next_word['word'],subsequent_word['word']])
                                            poss.extend([next_word_pos,subsequent_word_pos])
                                        else: # new phrase needs to be generated
                                            phrase = [word['word'],next_word['word'],subsequent_word['word']]
                                            poss = [pos,next_word_pos,subsequent_word_pos]
                                            ph = True
                                            ms = [m]
                            elif next_word_phrase == 'B-VP':
                                if len(sentence) > i+2:
                                    subsequent_words = []
                                    subsequent_words_pos = []
                                    for subsequent_word in sentence[i+2:]:
                                        if subsequent_word['phrase'][1:] == '-VP':
                                            subsequent_word_pos = subsequent_word['pos'].split('(')[0]
                                            subsequent_words.append(subsequent_word)
                                            subsequent_words_pos.append(subsequent_word_pos)
                                        else: # phrase is complete, complete information and go to end of loop
                                            if ph: # existing phrase is extended with another word
                                                ms.append(m)
                                                phrase.extend([next_word['word']] + [subsequent_word['word'] for subsequent_word in subsequent_words])
                                                poss.extend([next_word_pos] + subsequent_words_pos)
                                            else: # new phrase needs to be generated
                                                phrase = [word['word'],next_word['word']] + [subsequent_word['word'] for subsequent_word in subsequent_words]
                                                poss = [pos,next_word_pos] + subsequent_words_pos
                                                ph = True
                                                ms = [m]
                                            break
                                        
                            else: # complete phrase
                                if ph: 
                                    ms.append(m)
                                    output.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index]]))
                                    output_full.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index,sentext]]))
                                    ph = False
                                    ms = []
                                else:
                                    phrase = word['word']
                                    poss = pos
                                    output.append('\t'.join([str(x) for x in [m,phrase,poss,pol,review_index]]))
                                    output_full.append('\t'.join([str(x) for x in [m,phrase,poss,pol,review_index,sentext]]))
                    else: # just ADJ, complete phrase
                        if ph:
                            ms.append(m)
                            output.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index]]))
                            output_full.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index,sentext]]))
                            ph = False
                            ms = []
                        else:
                            phrase = word['word']
                            poss = pos        
                            output.append('\t'.join([str(x) for x in [m,phrase,poss,pol,review_index]]))
                            output_full.append('\t'.join([str(x) for x in [m,phrase,poss,pol,review_index,sentext]]))
                else: 
                    if ph:
                        output.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index]]))
                        output_full.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index,sentext]]))
                        ph = False
                        ms = []                      
            else:
                if ph:
                    output.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index]]))
                    output_full.append('\t'.join([str(x) for x in [' '.join(ms),' '.join(phrase),' '.join(poss),pol,review_index,sentext]]))
                    ph = False
                    ms = []                      

with open(outfile,'w',encoding='utf-8') as out:
    out.write('\n'.join(output))

with open(outfile_sentences,'w',encoding='utf-8') as out:
    out.write('\n'.join(output_full))

