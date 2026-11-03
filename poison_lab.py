import statistics

from robust_stats import robust_baseline


normal = [8, 9, 7, 10, 6, 8, 9, 7] * 7
spike = [1200, 1180, 1210, 1190]
data = normal + spike

mean, std_dev = statistics.mean(data), statistics.stdev(data)
median, sigma = robust_baseline(data)

print(f"Purana tareeka (mean, std_dev): {mean:.1f}, {std_dev:.1f}")
print(f"Naya tareeka   (median, MAD):   {median:.1f}, {sigma:.1f}")
print(
    f"100 errors/min ka z-score  ->  purana: {(100 - mean) / std_dev:.2f}   "
    f"naya: {(100 - median) / sigma:.2f}"
)
