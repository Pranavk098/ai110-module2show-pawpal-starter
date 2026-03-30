import streamlit as st
from pawpal_system import Pet, Owner, Task, Scheduler

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your personal pet care day-planner.")

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
    st.session_state["owner"] = None        # Owner object (or None until created)

if "pets" not in st.session_state:
    st.session_state["pets"] = []           # List[Pet]

if "tasks" not in st.session_state:
    st.session_state["tasks"] = []          # List[Task]

if "schedule" not in st.session_state:
    st.session_state["schedule"] = None     # Schedule object (or None until generated)

# ─────────────────────────────────────────────────────────────
#  Handy aliases so the rest of the code is less verbose
# ─────────────────────────────────────────────────────────────
def get_owner():   return st.session_state["owner"]
def get_pets():    return st.session_state["pets"]
def get_tasks():   return st.session_state["tasks"]
def get_schedule():return st.session_state["schedule"]


# ═════════════════════════════════════════════════════════════
#  SECTION 1 — OWNER SETUP
# ═════════════════════════════════════════════════════════════
st.header("Step 1 — Who are you?")

col_name, col_time = st.columns(2)
with col_name:
    owner_name = st.text_input("Your name", value="Jordan", key="input_owner_name")
with col_time:
    avail_mins = st.number_input(
        "Free minutes you have today",
        min_value=1, max_value=1440, value=90,
        key="input_avail_mins"
    )

if st.button("Save owner", key="btn_save_owner"):
    # Pull the current pet list from the vault so we don't lose pets
    # when the owner is updated.
    current_pets = get_pets()

    # Check: does an owner object already exist in the vault?
    #   YES → update its fields in-place (don't wipe the pet list)
    #   NO  → create a brand-new Owner and store it
    if get_owner() is not None:
        st.session_state["owner"].name              = owner_name
        st.session_state["owner"].available_minutes = avail_mins
        st.session_state["owner"].pets              = current_pets
        st.success(f"Owner updated: {owner_name} ({avail_mins} min available)")
    else:
        st.session_state["owner"] = Owner(
            name=owner_name,
            available_minutes=avail_mins,
            pets=current_pets
        )
        st.success(f"Owner created: {owner_name} ({avail_mins} min available)")

    # Clear any stale schedule whenever owner settings change
    st.session_state["schedule"] = None

# Show current owner status
if get_owner() is not None:
    o = get_owner()
    st.info(f"Current owner: **{o.name}** — {o.available_minutes} min available today")
else:
    st.warning("No owner saved yet. Fill in the fields above and click 'Save owner'.")


# ═════════════════════════════════════════════════════════════
#  SECTION 2 — PET MANAGEMENT
# ═════════════════════════════════════════════════════════════
st.divider()
st.header("Step 2 — Your Pets")

col_pet, col_species = st.columns(2)
with col_pet:
    pet_name = st.text_input("Pet name", value="Buddy", key="input_pet_name")
with col_species:
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"],
                           key="input_species")

if st.button("Add pet", key="btn_add_pet"):
    if get_owner() is None:
        st.error("Please save an owner first (Step 1) before adding pets.")
    else:
        # Check: is a pet with this name already in the vault?
        existing_names = [p.name.lower() for p in get_pets()]
        if pet_name.lower() in existing_names:
            st.warning(f"A pet named '{pet_name}' already exists.")
        else:
            new_pet = Pet(name=pet_name, species=species)
            st.session_state["pets"].append(new_pet)
            # Keep the Owner's pet list in sync with the vault
            st.session_state["owner"].pets = st.session_state["pets"]
            st.success(f"Added {pet_name} the {species}!")
            # Stale schedule no longer valid
            st.session_state["schedule"] = None

# Display pets currently in the vault
if get_pets():
    st.subheader("Registered pets")
    for i, pet in enumerate(get_pets(), start=1):
        col_info, col_del = st.columns([5, 1])
        with col_info:
            st.write(f"{i}. **{pet.name}** ({pet.species})")
        with col_del:
            if st.button("Remove", key=f"remove_pet_{i}"):
                st.session_state["pets"].pop(i - 1)
                if get_owner() is not None:
                    st.session_state["owner"].pets = st.session_state["pets"]
                st.session_state["schedule"] = None
                st.rerun()
else:
    st.info("No pets added yet.")


# ═════════════════════════════════════════════════════════════
#  SECTION 3 — TASK MANAGEMENT
# ═════════════════════════════════════════════════════════════
st.divider()
st.header("Step 3 — Care Tasks")
st.caption("Add everything you *want* to do today. The scheduler will decide what fits.")

col_t, col_d, col_p = st.columns(3)
with col_t:
    task_title = st.text_input("Task title", value="Morning Walk", key="input_task_title")
with col_d:
    duration = st.number_input("Duration (min)", min_value=1, max_value=480,
                                value=30, key="input_duration")
with col_p:
    priority = st.selectbox("Priority", ["high", "medium", "low"],
                             key="input_priority")

if st.button("Add task", key="btn_add_task"):
    if get_owner() is None:
        st.error("Please save an owner first (Step 1) before adding tasks.")
    else:
        try:
            new_task = Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority
            )
            st.session_state["tasks"].append(new_task)
            st.success(f"Task added: '{task_title}' ({duration} min, {priority} priority)")
            # Adding a task invalidates the old schedule
            st.session_state["schedule"] = None
        except ValueError as e:
            st.error(f"Could not add task: {e}")

# Display tasks currently in the vault
if get_tasks():
    st.subheader("Task list")
    for i, task in enumerate(get_tasks(), start=1):
        priority_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        icon = priority_colors.get(task.priority, "⚪")
        col_info, col_del = st.columns([5, 1])
        with col_info:
            st.write(f"{i}. {icon} **{task.title}** — {task.duration_minutes} min ({task.priority})")
        with col_del:
            if st.button("Remove", key=f"remove_task_{i}"):
                st.session_state["tasks"].pop(i - 1)
                st.session_state["schedule"] = None
                st.rerun()
else:
    st.info("No tasks added yet.")


# ═════════════════════════════════════════════════════════════
#  SECTION 4 — GENERATE SCHEDULE
# ═════════════════════════════════════════════════════════════
st.divider()
st.header("Step 4 — Generate Today's Schedule")

ready = get_owner() is not None and len(get_tasks()) > 0

if not ready:
    st.warning("Complete Steps 1 and 3 (owner + at least one task) before generating.")

if st.button("Generate schedule", disabled=not ready, key="btn_generate"):
    owner    = get_owner()
    tasks    = get_tasks()
    scheduler = Scheduler(owner=owner, tasks=tasks)
    schedule  = scheduler.generate()

    # Store the result in the vault so it survives the next rerun
    st.session_state["schedule"] = schedule
    st.success("Schedule generated! Scroll down to see your day.")


# ═════════════════════════════════════════════════════════════
#  SECTION 5 — DISPLAY SCHEDULE (read from vault)
# ═════════════════════════════════════════════════════════════
schedule = get_schedule()

if schedule is not None:
    owner = get_owner()
    st.divider()
    st.header(f"Today's Plan for {owner.name}")

    # ── Scheduled tasks ───────────────────────────────────────
    if not schedule.is_empty():
        st.subheader(
            f"Scheduled — {len(schedule.scheduled_tasks)} tasks, "
            f"{schedule.total_minutes_used} / {owner.available_minutes} min used"
        )
        for st_task in schedule.scheduled_tasks:
            priority_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            icon = priority_colors.get(st_task.task.priority, "⚪")
            with st.container(border=True):
                col_a, col_b = st.columns([3, 2])
                with col_a:
                    st.markdown(f"### {icon} {st_task.task.title}")
                    st.caption(f"Priority: {st_task.task.priority.upper()}")
                with col_b:
                    st.metric("Duration", f"{st_task.task.duration_minutes} min")
                    st.caption(f"Time: {st_task.time_label()}")
    else:
        st.error("No tasks could be scheduled within your available time.")

    # ── Skipped tasks ─────────────────────────────────────────
    if schedule.skipped_tasks:
        st.subheader(f"Skipped — {len(schedule.skipped_tasks)} tasks didn't fit")
        for task, reason in schedule.skipped_tasks:
            with st.expander(f"❌ {task.title} ({task.duration_minutes} min, {task.priority})"):
                st.write(f"**Reason:** {reason}")

    # ── Progress bar ──────────────────────────────────────────
    st.divider()
    pct = schedule.total_minutes_used / owner.available_minutes
    st.caption(f"Time used: {schedule.total_minutes_used} of {owner.available_minutes} min")
    st.progress(min(pct, 1.0))


# ═════════════════════════════════════════════════════════════
#  SECTION 6 — RESET (wipe the vault)
# ═════════════════════════════════════════════════════════════
st.divider()
if st.button("Reset everything", key="btn_reset"):
    # Clear every key we own in the vault
    for key in ["owner", "pets", "tasks", "schedule"]:
        st.session_state[key] = None if key in ("owner", "schedule") else []
    st.rerun()
