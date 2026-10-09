## 2026-10-09 - O(N^2) Bottleneck in numpy.correlate
**Learning:** numpy.correlate() operates in O(N^2) time for large arrays, causing a severe performance bottleneck during pitch estimation (taking ~24ms per call).
**Action:** Use FFT-based autocorrelation (np.fft.rfft and irfft) for large arrays instead of np.correlate to achieve O(N log N) performance.
