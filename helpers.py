import itertools


def parse_days(days: str):
    result = set()
    i = 0
    while i < len(days):
        if days[i] == "T" and i + 1 < len(days) and days[i+1] == "h":
            result.add("Th")
            i += 2
        elif days[i] == "R":
            result.add("Th")
            i += 1
        else:
            result.add(days[i])
            i += 1
    return result


def to_minutes(t):
    if not t:
        return None

    if "T" in t:
        t = t.split("T")[1]

    h, m = map(int, t.split(":")[:2])
    return h * 60 + m


def conflicts(s1, s2):
    days1 = s1.get("days") or ""
    days2 = s2.get("days") or ""
    shared_days = parse_days(days1) & parse_days(days2)

    if not shared_days:
        return False

    for t1 in s1.get("times", []):
        for t2 in s2.get("times", []):
            start1, end1 = t1
            start2, end2 = t2
            if start1 is None or end1 is None or start2 is None or end2 is None:
                continue
            if not (end1 <= start2 or end2 <= start1):
                return True

    return False


def score_schedule(schedule):
    # lower score is better
    days_on_campus = len(set(d for s in schedule for d in parse_days(s.get("days", ""))))

    start_times = [
        t[0]
        for s in schedule
        for t in s.get("times", [])
        if t[0] is not None
    ]
    avg_start = sum(start_times) / len(start_times) if start_times else 0

    total_gaps = 0
    day_sections = {}

    for s in schedule:
        for day in parse_days(s.get("days", "")):
            day_sections.setdefault(day, []).extend(s.get("times", []))

    for day, times in day_sections.items():
        sorted_times = sorted(
            (t[0], t[1]) for t in times if t[0] is not None and t[1] is not None
        )
        for i in range(1, len(sorted_times)):
            gap = sorted_times[i][0] - sorted_times[i-1][1]
            if gap > 0:
                total_gaps += gap

    return days_on_campus * 100 + total_gaps - avg_start * 0.1


def summarize_schedule(schedule):
    return [
        f"{s['course']} {s['component']} {s['section']} "
        f"{s['days']} {s['times']}"
        for s in schedule
    ]
