## 2023-10-27 - Vectorized audio features and FFT-based pitch estimation
**Learning:** Python for loops over small audio frames in acoustic feature extraction are extremely slow (O(n) Python overhead on O(n) loop), and `np.correlate(..., mode='full')` is O(N^2), causing a huge bottleneck for voice biometrics parsing.
**Action:** Always vectorize framing via `np.arange` + slicing when doing time-series windowing, and use FFT-based autocorrelation (`np.fft.irfft(fft * conj(fft))`) for pitch/lag estimation which reduces time complexity to O(N log N).
