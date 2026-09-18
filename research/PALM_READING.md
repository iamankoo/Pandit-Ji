# Research — AI Palm Reading

Pipeline:
image → quality check → hand detection → left/right classification → segmentation → landmarks/lines/mounts/fingers → structured visual evidence → palmistry rule engine → AI explanation → report.

Vision must output observable/estimated structures first. Reasoning maps those structures to traditional palmistry interpretations. The LLM must not invent invisible lines.

Evaluate across lighting, skin tones, hand sizes, camera quality, occlusion, left/right hands and line visibility.

Measure detection, segmentation, side classification, landmarks, line precision/recall and interpretation consistency.

Palm images require explicit purpose, retention and deletion controls.
