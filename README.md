# Product_review_summary
This repository harbours scripts that were used for the study described in the Coling 2018 paper 'Aspect-based summarization of pros and cons in unstructured product reviews'.

The scripts 'baseline.py' and 'synpat.py' are implementations of two of the systems that are evaluated in the paper. The script 'evaluation1.py' is the implementation of the first evaluation, that matches system output to the pros and cons that are put forward by the authors of the reviews. All scripts can be applied with python 3.x, and take json-formatted review text as basic input. These files can not be shared publicly. Please contact Florian Kunneman (f.kunneman@gmail.com) if you are interested in the data or have questions about the code. 

### Usage of baseline.py

python baseline.py train.json dev.json test.json baseline_predictions.json

### usage of synpat.py

python synpat.py test.json duoman.txt synpat_predictions.txt synpat_predictions.json

### usage of evaluation1.py

python evaluation1.py synpat_predictions.json human_gold_standard.json 70 pattern_pros pattern_cons pattern_results.json pattern_results_summary.csv