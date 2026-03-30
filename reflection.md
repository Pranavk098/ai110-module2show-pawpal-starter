# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
Owner owns 1..* Pet objects.
Scheduler uses one Owner, processes many Task objects, and produces one Schedule.
Schedule contains many ScheduledTask objects, each wrapping one Task.
- What classes did you include, and what responsibilities did you assign to each?
Pet — stores name and species
Owner — stores name, available minutes, and a list of pets
Task — stores title, duration, priority; computes its own priority rank
ScheduledTask — wraps a Task and adds a start time; computes end time
Schedule — holds accepted ScheduledTask list and skipped tasks with reasons
Scheduler — takes an Owner + Task list, sorts by priority, checks time fit, returns a completed Schedule

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers five categories of constraint, in the order they were
deemed most important for a real pet-owner's day:

1. **Time budget (hard cap)**
   `Owner.available_minutes` is a strict ceiling. No schedule will ever exceed
   it. This was made the primary constraint because a pet owner with 90 minutes
   free simply cannot do 3 hours of tasks — the scheduler must make hard
   choices rather than produce an unrealistic plan.

2. **Priority level (high / medium / low)**
   The greedy pass works in priority-first order: all "high" tasks are
   attempted before any "medium" task is even considered. This ensures that
   critical activities (medication, feeding) are always given slots first.
   Priority was chosen as the second constraint because missing a high-priority
   task has real consequences (a dog goes unfed) whereas missing a low-priority
   task (a leisurely stroll) does not.

3. **Dependency ordering**
   `Task.depends_on` is resolved through a topological sort (Kahn's algorithm
   with a priority-weighted heap). A task like "Give Medicine" that depends on
   "Feed Breakfast" is never placed before its dependency, regardless of
   priority rank.

4. **Time windows (earliest_start / deadline)**
   `earliest_start_minute` advances the scheduler clock forward when a task
   cannot begin yet (e.g., a vet appointment not until 10 AM). `deadline_minute`
   causes the task to be skipped entirely if it cannot finish in time. These
   were added after the core greedy logic because they represent real-world
   hard constraints that the greedy pass alone cannot express.

5. **Buffer gaps**
   `Owner.buffer_minutes` inserts a mandatory rest period between every task.
   This was ranked last because it is optional: most tasks in a pet-care day
   do not require cooldown time, so it defaults to zero.

How the priority order was decided:
The guiding principle was "what causes the most harm if missed?" Time budget
and critical tasks (feeding, medication) ranked highest. Preferences and
convenience features (buffer time, preferred start times) ranked lowest.

**b. Tradeoffs**

**Tradeoff 1 — Greedy priority-first vs. optimal packing**

The scheduler uses a greedy algorithm: it sorts tasks from highest to lowest
priority and places each one into the next available time slot. It never
reconsiders a decision once made.

- *What this gives up:* Optimality. A single large high-priority task (e.g.,
  a 50-minute grooming session) can consume so much of the budget that several
  smaller medium-priority tasks, which together would fit, are all skipped.
  A knapsack-style optimizer could find a combination with a higher total
  priority score, but at significant implementation complexity.

- *Why it is reasonable here:* A pet owner's intuition already matches greedy
  thinking — "do the most important things first, stop when time runs out."
  The fill-the-gap second pass (Step 4 of `generate()`) partially compensates
  by rescuing small tasks that fit in leftover minutes. For task lists of
  under 20 items the greedy result is almost always identical to the optimal
  one, so the simpler algorithm wins.

**Tradeoff 2 — preferred_time is advisory, not enforced**

`Task.preferred_time` ("HH:MM") stores the owner's intended wall-clock time
for a task, but the greedy scheduler ignores it during placement. It only uses
`preferred_time` in two places: `sort_by_time()` (manual sorting utility) and
`_check_time_overlaps()` (warning detection). The scheduler still places tasks
sequentially by priority, so a task with `preferred_time="07:00"` may end up
at 9:30 AM in the final schedule.

- *What this gives up:* Clock-accurate scheduling. A "Morning Walk" tagged
  07:00 will not actually appear at 07:00 on the timeline unless `earliest_start_minute`
  is also set. The overlap warning fires correctly, but the schedule itself
  does not honour the preferred slot.

- *Why it is reasonable here:* Enforcing preferred_time as a hard fixed-start
  would require the scheduler to leave intentional gaps in the timeline (idle
  time between tasks) and would complicate the fill-the-gap pass significantly.
  For the current stage of the app — where the owner is told "here is what fits
  in your day" rather than "here is your minute-by-minute timetable" — advisory
  preferred times plus clear conflict warnings are a good balance between
  simplicity and usefulness.

**Simplification opportunities identified in the codebase**

1. `_topological_sort()` uses a min-heap for priority tie-breaking inside
   Kahn's algorithm. For task lists under ~30 items (the realistic maximum for
   a pet-care day) a simple `deque`-based Kahn's pass followed by a stable
   `sorted()` on the result would be equally correct, faster to read, and
   require no `heapq` import. The heap adds roughly 15 lines of complexity to
   save microseconds that will never be noticed.

2. `_check_time_overlaps()` and `_check_conflicts()` both iterate over all
   pairs with nested `for` loops — O(n²). This is perfectly fine for n < 20.
   A sorted-interval sweep (sort by start, then one linear pass) would reduce
   this to O(n log n), but would make the code significantly harder to read
   for no practical gain at this scale.

3. `priority_rank()` creates a new dictionary `{"high": 3, "medium": 2, "low": 1}`
   on every call. Moving it to a class-level constant (`_RANK = {...}`) and
   returning `self._RANK[self.priority]` avoids a small repeated allocation.

4. The skip-reason strings in `generate()` ("Not enough time", "No time left")
   are plain strings that `_fill_gaps()` must inspect with `in` substring
   checks. Replacing these with a structured `SkipReason` enum or a short
   reason code would remove the string-parsing fragility entirely.

5. `filter_by_status()` validates its `status` argument against
   `Task.VALID_STATUSES`. The same pattern could be applied to
   `filter_by_pet()` — currently if the pet name does not match any task,
   it silently returns an empty list with no feedback to the caller.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
