# Paired source-edit experiment

The panel contains ten changes to legal meaning and three meaning-preserving controls. Each input starts from its own release baseline and passes through the normal exporter. R2.zip contains the second-round release. R3-first-assessment.zip contains the frozen first assessment. R3-final.zip includes the two post-challenge repairs for F09 and F10.

Run the following in this folder with Python 3 and lxml installed.

```shell
python3 -m zipfile -e R2.zip r2
python3 -m zipfile -e R3-first-assessment.zip first
python3 -m zipfile -e R3-final.zip final
python3 final/experiments/paired_experiment.py --r2-root r2 --r3-root first --output replay-first.csv
python3 final/experiments/paired_experiment.py --r2-root r2 --r3-root final --output replay-after.csv
python3 final/verify.py --baseline-r2 r2/PIPL-model.json
```

Compare the outputs with first_assessment.csv and post_repair_regression.csv. The former reports 8/10 selected faults detected, the latter 10/10 on the same panel after the known misses were addressed. All three controls are accepted at each stage. The earlier XML-only and AKN experiments are in the sibling supplement directories.
