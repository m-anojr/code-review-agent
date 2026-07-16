def find_max(values):
    """Find the maximum value in a list. Has an off-by-one error."""
    if not values:
        return None
    max_val = values[0]
    # bug: range should go to len(values), not len(values) - 1
    for i in range(1, len(values) - 1):
        if values[i] > max_val:
            max_val = values[i]
    return max_val


def paginate(items, page, page_size):
    """Return a page of items. Off-by-one in slice."""
    start = page * page_size
    # bug: end should be start + page_size, this misses the last item per page
    end = start + page_size - 1
    return items[start:end]
