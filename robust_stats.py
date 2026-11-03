import statistics


def robust_baseline(values):
    """Return a spike-resistant center and scale using the median and MAD."""
    median = statistics.median(values)
    mad = statistics.median([abs(value - median) for value in values])
    sigma = max(1.4826 * mad, median**0.5, 1.0)
    return median, sigma
