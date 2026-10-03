## 2023-10-03 - Cache MFCC Computations
**Learning:** Pure python or numpy feature extraction tasks (like computing DCT-II basis or filterbanks in `core/speaker_recognition.py`) run redundantly in loops and become major bottlenecks if not cached, as they only depend on constant parameters (num_filters, num_ceps, sample_rate, nfft).
**Action:** When extracting audio features repeatedly, always cache static transformation matrices based on their configuration parameters to skip repeated computation overhead.
