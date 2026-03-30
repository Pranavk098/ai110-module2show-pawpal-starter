import os
import streamlit as st
from pawpal_system import Pet, Owner, Task, Scheduler

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("A calm, structured assistant for planning your pet-care day.")

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Manrope', sans-serif;
        }

        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
        }

        .pp-card {
            border: 1px solid rgba(140, 140, 140, 0.20);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            background: linear-gradient(135deg, rgba(40, 56, 86, 0.32), rgba(15, 20, 38, 0.18));
            margin-bottom: 0.9rem;
            min-height: 94px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        }

        .pp-chip-row {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin: 0.35rem 0 0.8rem 0;
        }

        .pp-chip {
            border: 1px solid rgba(130, 170, 255, 0.35);
            border-radius: 999px;
            padding: 0.28rem 0.7rem;
            font-size: 0.84rem;
            color: #c8d8ff;
            background: rgba(53, 84, 161, 0.20);
        }

        [data-testid="stTabs"] button {
            border-radius: 10px;
            padding: 0.45rem 0.8rem;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.45rem;
            font-weight: 800;
        }

        .stButton > button {
            border-radius: 10px;
            border: 1px solid rgba(140, 160, 200, 0.28);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_a, hero_b, hero_c = st.columns(3)
with hero_a:
    st.markdown('<div class="pp-card"><strong>🧠 Plan smarter</strong><br/>Priority-aware scheduling with realistic constraints.</div>', unsafe_allow_html=True)
with hero_b:
    st.markdown('<div class="pp-card"><strong>⚠️ See conflicts early</strong><br/>Warnings highlight risks before your day starts.</div>', unsafe_allow_html=True)
with hero_c:
    st.markdown('<div class="pp-card"><strong>✅ Act confidently</strong><br/>Clear views help you make fast, safe decisions.</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="pp-chip-row">'
    '<span class="pp-chip">Setup</span>'
    '<span class="pp-chip">Task Builder</span>'
    '<span class="pp-chip">Smart Generation</span>'
    '<span class="pp-chip">Conflict Guidance</span>'
    '</div>',
    unsafe_allow_html=True,
)

DATA_FILE = "data.json"

# ═════════════════════════════════════════════════════════════
#  SECTION 0 — SESSION STATE "VAULT"
#
#  Streamlit reruns this entire script on every interaction.
#  st.session_state works like a dictionary that SURVIVES each
#  rerun.  The pattern below:
#
#      if "key" not in st.session_state:
#          st.session_state["key"] = <default>
#
#  reads as: "only initialise this value the very first time
#  the app loads; after that, leave whatever the user has
#  already built completely untouched."
# ═════════════════════════════════════════════════════════════

if "owner" not in st.session_state:
    try:
        loaded_owner, loaded_tasks = Owner.load_from_json(DATA_FILE)
        st.session_state["owner"] = loaded_owner
        st.session_state["pets"] = loaded_owner.pets
        st.session_state["tasks"] = loaded_tasks
        st.session_state["schedule"] = None
        st.session_state["load_message"] = f"Loaded saved data from {DATA_FILE}."
    except FileNotFoundError:
        st.session_state["owner"] = None
        st.session_state["pets"] = []
        st.session_state["tasks"] = []
        st.session_state["schedule"] = None
    except (ValueError, OSError) as exc:
        st.session_state["owner"] = None
        st.session_state["pets"] = []
        st.session_state["tasks"] = []
        st.session_state["schedule"] = None
        st.session_state["load_error"] = (
            f"Could not load saved data ({exc}). Starting with an empty session."
        )

# Backward-compatible key initialization for older in-memory sessions.
if "pets" not in st.session_state:
    st.session_state["pets"] = []
if "tasks" not in st.session_state:
    st.session_state["tasks"] = []
if "schedule" not in st.session_state:
    st.session_state["schedule"] = None

# ─────────────────────────────────────────────────────────────
#  Handy aliases so the rest of the code is less verbose
# ─────────────────────────────────────────────────────────────
def get_owner():   return st.session_state["owner"]
def get_pets():    return st.session_state["pets"]
def get_tasks():   return st.session_state["tasks"]
def get_schedule():return st.session_state["schedule"]


def persist_state() -> bool:
    """Persist owner, pets, and tasks to disk; returns True when successful."""
    owner = get_owner()
    if owner is None:
        return False

    owner.pets = get_pets()
    owner.save_to_json(tasks=get_tasks(), filepath=DATA_FILE)
    return True


if "load_message" in st.session_state:
    st.success(st.session_state.pop("load_message"))
if "load_error" in st.session_state:
    st.warning(st.session_state.pop("load_error"))


# Sidebar summary and safe reset controls.
with st.sidebar:
    st.subheader("Workspace Status")
    st.markdown(f"- 👤 Owner: **{'Set' if get_owner() else 'Not set'}**")
    st.markdown(f"- 🐾 Pets: **{len(get_pets())}**")
    st.markdown(f"- 📝 Tasks: **{len(get_tasks())}**")
    st.markdown(f"- 📅 Schedule: **{'Ready' if get_schedule() else 'Not generated'}**")
    st.divider()
    confirm_reset = st.checkbox("I understand this clears all saved data", key="confirm_reset")
    if st.button("Reset everything", key="btn_reset", type="secondary"):
        if not confirm_reset:
            st.warning("Please confirm reset using the checkbox first.")
        else:
            for key in ["owner", "pets", "tasks", "schedule"]:
                st.session_state[key] = None if key in ("owner", "schedule") else []
            try:
                if os.path.exists(DATA_FILE):
                    os.remove(DATA_FILE)
            except OSError as exc:
                st.error(f"Could not clear {DATA_FILE}: {exc}")
            st.rerun()

tab_setup, tab_tasks, tab_generate, tab_results = st.tabs(
    ["1. Setup", "2. Tasks", "3. Generate", "4. Results"]
)

with tab_setup:
    st.header("Step 1 — Owner")
    col_name, col_time = st.columns(2)
    with col_name:
        owner_name = st.text_input("Your name", value=(get_owner().name if get_owner() else "Jordan"), key="input_owner_name")
    with col_time:
        owner_default_minutes = get_owner().available_minutes if get_owner() else 90
        avail_mins = st.number_input(
            "Free minutes you have today",
            min_value=1, max_value=1440, value=owner_default_minutes,
            key="input_avail_mins"
        )

    if st.button("Save owner", key="btn_save_owner", type="primary"):
        current_pets = get_pets()
        if get_owner() is not None:
            st.session_state["owner"].name = owner_name
            st.session_state["owner"].available_minutes = avail_mins
            st.session_state["owner"].pets = current_pets
            st.success(f"Owner updated: {owner_name} ({avail_mins} min available)")
        else:
            st.session_state["owner"] = Owner(
                name=owner_name,
                available_minutes=avail_mins,
                pets=current_pets
            )
            st.success(f"Owner created: {owner_name} ({avail_mins} min available)")

        st.session_state["schedule"] = None
        try:
            if persist_state():
                st.info(f"Saved to {DATA_FILE}.")
        except OSError as exc:
            st.error(f"Failed to save data: {exc}")

    if get_owner() is not None:
        o = get_owner()
        st.info(f"Current owner: **{o.name}** — {o.available_minutes} min available today")
    else:
        st.warning("No owner saved yet.")

    st.divider()
    st.header("Step 2 — Pets")

    col_pet, col_species = st.columns(2)
    with col_pet:
        pet_name = st.text_input("Pet name", value="Buddy", key="input_pet_name")
    with col_species:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"], key="input_species")

    if st.button("Add pet", key="btn_add_pet"):
        if get_owner() is None:
            st.error("Please save an owner first before adding pets.")
        else:
            existing_names = [p.name.lower() for p in get_pets()]
            if pet_name.lower() in existing_names:
                st.warning(f"A pet named '{pet_name}' already exists.")
            else:
                new_pet = Pet(name=pet_name, species=species)
                st.session_state["pets"].append(new_pet)
                st.session_state["owner"].pets = st.session_state["pets"]
                st.session_state["schedule"] = None
                st.success(f"Added {pet_name} the {species}!")
                try:
                    if persist_state():
                        st.info(f"Saved to {DATA_FILE}.")
                except OSError as exc:
                    st.error(f"Failed to save data: {exc}")

    if get_pets():
        st.subheader("Registered pets")
        for i, pet in enumerate(get_pets(), start=1):
            col_info, col_del = st.columns([5, 2])
            with col_info:
                st.write(f"{i}. **{pet.name}** ({pet.species})")
            with col_del:
                if st.button("Remove", key=f"remove_pet_{i}"):
                    removed_pet = st.session_state["pets"].pop(i - 1)
                    # Unassign tasks that were linked to the removed pet.
                    for task in st.session_state["tasks"]:
                        if task.pet == removed_pet:
                            removed_pet.remove_task(task)
                    if get_owner() is not None:
                        st.session_state["owner"].pets = st.session_state["pets"]
                    st.session_state["schedule"] = None
                    try:
                        if persist_state():
                            st.info(f"Saved to {DATA_FILE}.")
                    except OSError as exc:
                        st.error(f"Failed to save data: {exc}")
                    st.rerun()
    else:
        st.info("No pets added yet.")

with tab_tasks:
    st.header("Step 3 — Care Tasks")
    st.caption("Add everything you want to do today. The scheduler will decide what fits.")

    col_t, col_d, col_p = st.columns(3)
    with col_t:
        task_title = st.text_input("Task title", value="Morning Walk", key="input_task_title")
    with col_d:
        duration = st.number_input("Duration (min)", min_value=1, max_value=480, value=30, key="input_duration")
    with col_p:
        priority = st.selectbox("Priority", ["high", "medium", "low"], key="input_priority")

    is_mobile = st.session_state.get("_is_mobile_layout", False)
    cols = st.columns(1 if is_mobile else 3)
    with cols[0]:
        task_category = st.selectbox(
            "Category",
            ["feeding", "exercise", "grooming", "medical", "play", "training", "hygiene", "other"],
            key="input_task_category",
        )
    if len(cols) > 1:
        with cols[1]:
            pet_options = ["(Any pet)"] + [p.name for p in get_pets()]
            selected_pet_name = st.selectbox("Assign to pet", pet_options, key="input_task_pet")
        with cols[2]:
            use_preferred_time = st.checkbox("Set preferred time", key="input_use_pref_time")
            preferred_time_obj = st.time_input("Preferred start time", key="input_pref_time", disabled=not use_preferred_time)
    else:
        pet_options = ["(Any pet)"] + [p.name for p in get_pets()]
        selected_pet_name = st.selectbox("Assign to pet", pet_options, key="input_task_pet")
        use_preferred_time = st.checkbox("Set preferred time", key="input_use_pref_time")
        preferred_time_obj = st.time_input("Preferred start time", key="input_pref_time", disabled=not use_preferred_time)

    preferred_time = preferred_time_obj.strftime("%H:%M") if use_preferred_time else None
    selected_pet = next((p for p in get_pets() if p.name == selected_pet_name), None)

    if st.button("Add task", key="btn_add_task", type="primary"):
        if get_owner() is None:
            st.error("Please save an owner first before adding tasks.")
        else:
            try:
                new_task = Task(
                    title=task_title,
                    duration_minutes=int(duration),
                    priority=priority,
                    pet=selected_pet,
                    category=task_category,
                    preferred_time=preferred_time,
                )
                if selected_pet is not None:
                    selected_pet.add_task(new_task)
                st.session_state["tasks"].append(new_task)
                st.session_state["schedule"] = None
                st.success(f"Task added: '{task_title}' ({duration} min, {priority}, {task_category})")
                try:
                    if persist_state():
                        st.info(f"Saved to {DATA_FILE}.")
                except OSError as exc:
                    st.error(f"Failed to save data: {exc}")
            except ValueError as e:
                st.error(f"Could not add task: {e}")

    if get_tasks():
        st.subheader("Task list")
        task_rows = []
        for i, task in enumerate(get_tasks(), start=1):
            task_rows.append({
                "#": i,
                "Title": task.title,
                "Pet": task.pet.name if task.pet else "Any",
                "Category": task.category,
                "Preferred Time": task.preferred_time or "-",
                "Duration (min)": task.duration_minutes,
                "Priority": task.priority,
                "Status": task.status,
            })
        st.dataframe(task_rows, use_container_width=True, hide_index=True)

        col_remove, col_confirm, col_remove_btn = st.columns([3, 2, 1])
        with col_remove:
            remove_task_choice = st.selectbox(
                "Remove a task",
                options=[f"{idx}. {t.title}" for idx, t in enumerate(get_tasks(), start=1)],
                key="input_remove_task_choice",
            )
        with col_confirm:
            confirm_delete = st.checkbox("Confirm task deletion", key="confirm_task_delete")
        with col_remove_btn:
            if st.button("Delete", key="btn_remove_task"):
                if not confirm_delete:
                    st.warning("Check 'Confirm task deletion' first.")
                else:
                    remove_index = int(remove_task_choice.split(".", 1)[0]) - 1
                    removed_task = st.session_state["tasks"].pop(remove_index)
                    if removed_task.pet is not None:
                        removed_task.pet.remove_task(removed_task)
                    st.session_state["schedule"] = None
                    try:
                        if persist_state():
                            st.info(f"Saved to {DATA_FILE}.")
                    except OSError as exc:
                        st.error(f"Failed to save data: {exc}")
                    st.rerun()

        with st.expander("Advanced Task Explorer", expanded=False):
            st.caption("Use scheduler helpers to sort and filter tasks before generating the plan.")
            task_scheduler = Scheduler(owner=get_owner(), tasks=get_tasks())

            col_sort, col_filter_pet, col_filter_status = st.columns(3)
            with col_sort:
                sort_mode = st.selectbox("Sort", ["Original order", "Preferred time"], key="input_sort_mode")
            with col_filter_pet:
                pet_filter = st.selectbox("Filter by pet", ["All pets"] + [p.name for p in get_pets()], key="input_filter_pet")
            with col_filter_status:
                status_filter = st.selectbox("Filter by status", ["All statuses", "pending", "done", "skipped"], key="input_filter_status")

            explorer_tasks = list(get_tasks())
            if pet_filter != "All pets":
                explorer_tasks = task_scheduler.filter_by_pet(pet_filter, tasks=explorer_tasks)
            if status_filter != "All statuses":
                explorer_tasks = task_scheduler.filter_by_status(status_filter, tasks=explorer_tasks)
            if sort_mode == "Preferred time":
                explorer_tasks = task_scheduler.sort_by_time(tasks=explorer_tasks)

            if explorer_tasks:
                explorer_rows = []
                for t in explorer_tasks:
                    explorer_rows.append({
                        "Title": t.title,
                        "Pet": t.pet.name if t.pet else "Any",
                        "Preferred Time": t.preferred_time or "-",
                        "Priority": t.priority,
                        "Status": t.status,
                    })
                st.success(f"Showing {len(explorer_rows)} task(s) after sorting/filtering.")
                st.dataframe(explorer_rows, use_container_width=True, hide_index=True)
            else:
                st.warning("No tasks match the selected filters.")
    else:
        st.info("No tasks added yet.")

with tab_generate:
    st.header("Step 4 — Generate Today's Schedule")
    ready = get_owner() is not None and len(get_tasks()) > 0

    check_a, check_b = st.columns(2)
    with check_a:
        if get_owner():
            st.success("Owner saved")
        else:
            st.error("Owner not saved")
    with check_b:
        if get_tasks():
            st.success(f"{len(get_tasks())} task(s) ready")
        else:
            st.error("No tasks yet")

    if not ready:
        st.warning("Complete setup and add at least one task to enable schedule generation.")

    if st.button("Generate schedule", disabled=not ready, key="btn_generate", type="primary"):
        owner = get_owner()
        tasks = get_tasks()
        scheduler = Scheduler(owner=owner, tasks=tasks)
        st.session_state["schedule"] = scheduler.generate()
        st.success("Schedule generated. Open the Results tab.")

with tab_results:
    schedule = get_schedule()
    if schedule is None:
        st.info("No schedule yet. Go to Generate tab and click 'Generate schedule'.")
    else:
        owner = get_owner()
        st.header(f"Today's Plan for {owner.name}")

        metrics_a, metrics_b, metrics_c, metrics_d = st.columns(4)
        with metrics_a:
            st.metric("Scheduled", len(schedule.scheduled_tasks))
        with metrics_b:
            st.metric("Skipped", len(schedule.skipped_tasks))
        with metrics_c:
            st.metric("Warnings", len(schedule.warnings))
        with metrics_d:
            st.metric("Efficiency", f"{schedule.efficiency_score(owner.available_minutes)}%")

        result_plan, result_skipped, result_warnings = st.tabs([
            "Scheduled Plan", "Skipped Tasks", "Conflict Warnings"
        ])

        with result_plan:
            if not schedule.is_empty():
                sorted_scheduled = schedule.tasks_sorted_by_start()
                plan_rows = []
                for st_task in sorted_scheduled:
                    plan_rows.append({
                        "Time": st_task.time_label(owner.day_start_hour),
                        "Task": st_task.task.title,
                        "Pet": st_task.task.pet.name if st_task.task.pet else "Any",
                        "Category": st_task.task.category,
                        "Priority": st_task.task.priority,
                        "Duration (min)": st_task.task.duration_minutes,
                        "Status": st_task.task.status,
                    })
                st.dataframe(plan_rows, use_container_width=True, hide_index=True)
                st.success("Plan generated in chronological order and ready to follow.")
            else:
                st.error("No tasks could be scheduled within available time.")

        with result_skipped:
            if schedule.skipped_tasks:
                skipped_rows = []
                for task, reason in schedule.skipped_tasks:
                    skipped_rows.append({
                        "Task": task.title,
                        "Pet": task.pet.name if task.pet else "Any",
                        "Duration (min)": task.duration_minutes,
                        "Priority": task.priority,
                        "Reason": reason,
                    })
                st.warning(f"{len(schedule.skipped_tasks)} task(s) were skipped due to constraints.")
                st.dataframe(skipped_rows, use_container_width=True, hide_index=True)
            else:
                st.success("No tasks were skipped.")

        with result_warnings:
            if schedule.warnings:
                st.warning("Potential conflicts detected. Review each warning and suggested action.")
                warning_help = {
                    "time_overlap": (
                        "Time overlap",
                        "Two tasks collide in the same time window.",
                        "Shift one preferred time so tasks no longer overlap.",
                    ),
                    "double_feeding": (
                        "Double feeding risk",
                        "Feeding tasks are too close together.",
                        "Space feeding tasks at least 120 minutes apart.",
                    ),
                    "exercise_after_meal": (
                        "Exercise too soon after feeding",
                        "Dogs need at least 30 minutes rest after meals.",
                        "Move exercise later or feed earlier.",
                    ),
                    "duplicate_task": (
                        "Duplicate task title",
                        "Similar tasks may represent accidental duplication.",
                        "Merge duplicates or rename tasks clearly.",
                    ),
                    "circular_dependency": (
                        "Dependency cycle",
                        "Task dependencies loop back on each other.",
                        "Remove or simplify dependency links.",
                    ),
                }
                for i, warn in enumerate(schedule.warnings, start=1):
                    title, why_it_matters, suggested_action = warning_help.get(
                        warn.warning_type,
                        (
                            f"{warn.warning_type.replace('_', ' ').title()}",
                            "This warning indicates a planning risk.",
                            "Review the task details and adjust timing or priorities.",
                        ),
                    )
                    with st.expander(f"{i}. {title}"):
                        st.write(f"**Why this matters:** {why_it_matters}")
                        st.write(f"**Details:** {warn.message}")
                        if warn.tasks:
                            st.dataframe(
                                [{"Task": t.title, "Pet": t.pet.name if t.pet else "Any"} for t in warn.tasks],
                                use_container_width=True,
                                hide_index=True,
                            )
                        st.info(f"Suggested action: {suggested_action}")
            else:
                st.success("No conflicts detected. Your plan looks safe and consistent.")

        st.divider()
        pct = schedule.total_minutes_used / owner.available_minutes
        st.caption(f"Time used: {schedule.total_minutes_used} of {owner.available_minutes} min")
        st.progress(min(pct, 1.0))

        with st.expander("Show technical schedule summary"):
            st.code(schedule.summary())
