"""Deterministic, capacity-limited academic recovery scheduler."""
from datetime import date, timedelta
from dataclasses import dataclass
from collections import defaultdict
import math

@dataclass
class StudyTask:
    id: int
    title: str
    subject: str
    minutes: int
    done_minutes: int
    deadline: date
    priority: int = 2  # 1 low, 2 medium, 3 high

    @property
    def remaining(self):
        return max(0, self.minutes - self.done_minutes)


def validate_task(title, subject, minutes, deadline, priority=2):
    if not str(title).strip() or not str(subject).strip():
        raise ValueError('Task name and subject are required.')
    if not isinstance(minutes, int) or not 1 <= minutes <= 100000:
        raise ValueError('Duration must be between 1 and 100,000 minutes.')
    if not isinstance(deadline, date):
        raise ValueError('Choose a valid deadline.')
    if priority not in (1, 2, 3):
        raise ValueError('Priority must be Low, Medium, or High.')


def plan(tasks, daily_hours=2.0, today=None, days=30, unavailable=None, weekday_hours=None):
    """Return scheduled sessions and deadline feasibility.

    Capacity is study minutes per day. A deadline includes its calendar day.
    Every task is scheduled only through its deadline; unscheduled minutes are explicit.
    Session sizes max 50 min; last small fragments are legitimate.
    """
    today = today or date.today()
    unavailable = set(unavailable or [])
    weekday_hours = weekday_hours or {}
    if not 0 <= daily_hours <= 24:
        raise ValueError('Daily hours must be between 0 and 24.')
    if not 1 <= days <= 366:
        raise ValueError('Planning horizon must be 1–366 days.')
    active = [t for t in tasks if t.remaining > 0]
    pending = {t.id: t.remaining for t in active}
    sessions = []
    capacities = {}
    deadline_end = max([today + timedelta(days=days-1)] + [t.deadline for t in active])
    # Bound planning to 366 days; dates beyond horizon appear as unscheduled work, not falsely feasible.
    end = min(deadline_end, today + timedelta(days=days-1))
    for n in range((end - today).days + 1):
        day = today + timedelta(days=n)
        hours = weekday_hours.get(day.weekday(), daily_hours)
        if not 0 <= hours <= 24:
            raise ValueError('Daily availability must be 0–24 hours.')
        available = 0 if day in unavailable else int(round(hours * 60))
        capacities[day] = available
        while available:
            eligible = [t for t in active if pending[t.id] > 0 and t.deadline >= day]
            if not eligible:
                break
            eligible.sort(key=lambda t: (t.deadline, -t.priority, t.remaining, t.id))
            t = eligible[0]
            amount = min(50, available, pending[t.id])
            sessions.append({'date':day, 'task_id':t.id, 'title':t.title,
                             'subject':t.subject, 'minutes':amount, 'deadline':t.deadline})
            pending[t.id] -= amount
            available -= amount
    # Feasibility at each deadline is determined by actual allocation, not total-hours guesses.
    allocated = defaultdict(int)
    for s in sessions:
        allocated[s['task_id']] += s['minutes']
    shortfalls = []
    for t in sorted(active, key=lambda x:(x.deadline,-x.priority)):
        missing = t.remaining - allocated[t.id]
        if missing:
            shortfalls.append({'task_id':t.id, 'title':t.title,
                               'minutes':missing, 'deadline':t.deadline,
                               'overdue':t.deadline < today})
    today_sessions = [s for s in sessions if s['date'] == today]
    total_remaining = sum(t.remaining for t in active)
    total_available = sum(capacities.values())
    return {'sessions':sessions, 'today':today_sessions, 'shortfalls':shortfalls,
            'remaining_minutes':total_remaining, 'capacity_minutes':total_available,
            'unscheduled_minutes':sum(x['minutes'] for x in shortfalls),
            'feasible':not shortfalls, 'capacities':capacities,
            'allocated_minutes':sum(allocated.values())}


def next_step(tasks, result, today=None):
    """Prefer today's first scheduled session; never fabricate work."""
    if result['today']:
        return result['today'][0]
    if result['sessions']:
        return result['sessions'][0]
    return None


def deadline_summary(tasks, daily_hours, today=None, unavailable=None, weekday_hours=None):
    today = today or date.today()
    unfinished = sorted((t for t in tasks if t.remaining), key=lambda x:x.deadline)
    rows = []
    for deadline in sorted(set(t.deadline for t in unfinished)):
        due = [t for t in unfinished if t.deadline <= deadline]
        required = sum(t.remaining for t in due)
        capacity = 0
        for offset in range(max(0, (deadline-today).days+1)):
            d = today + timedelta(days=offset)
            if d not in (unavailable or set()):
                capacity += round((weekday_hours or {}).get(d.weekday(), daily_hours)*60)
        rows.append({'deadline':deadline,'required_minutes':required,
                     'capacity_minutes':capacity,'shortfall_minutes':max(0, required-capacity),
                     'days':max(0,(deadline-today).days+1),
                     'daily_required_hours':required/60/max(1,(deadline-today).days+1)})
    return rows
