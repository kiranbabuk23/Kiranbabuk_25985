# frontend_fin.py
import streamlit as st
import pandas as pd
from backend import DatabaseManager
from datetime import date
import altair as alt

# --- Configuration ---
DB_NAME = "Performance_db"
DB_USER = "postgres"  # Replace with your PostgreSQL username
DB_PASSWORD = "Kiran2001##"  # Replace with your PostgreSQL password
DB_HOST = "localhost"
DB_PORT = "5432"

db_manager = DatabaseManager(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
db_manager.connect()
db_manager.setup_database()

st.title("🎯 Performance Management System")
st.sidebar.header("User Selection")

# --- User Management (Login Simulation) ---
employees = db_manager.read_employees()
employee_options = {emp[1]: emp[0] for emp in employees}
is_manager_dict = {emp[1]: emp[2] for emp in employees}

selected_user_name = st.sidebar.selectbox("Select User", list(employee_options.keys()))
selected_user_id = employee_options.get(selected_user_name)
is_manager = is_manager_dict.get(selected_user_name, False)

st.sidebar.markdown(f"**Role:** {'Manager' if is_manager else 'Employee'}")

# --- Navigation ---
page = st.sidebar.radio("Go to", ["Dashboard", "Goal Management", "Feedback & History", "Business Insights"])

# --- Dashboard ---
if page == "Dashboard":
    st.header(f"Welcome, {selected_user_name}! 👋")
    
    st.subheader("Your Goals")
    user_goals = db_manager.read_goals(selected_user_id)
    if user_goals:
        goals_df = pd.DataFrame(user_goals, columns=["ID", "Description", "Due Date", "Status", "Manager"])
        st.dataframe(goals_df.set_index('ID'))
    else:
        st.info("You don't have any goals set yet.")
    
    st.markdown("---")

    st.subheader("Recent Feedback")
    user_feedback = db_manager.read_feedback(selected_user_id)
    if user_feedback:
        feedback_df = pd.DataFrame(user_feedback, columns=["Goal", "Comments", "Date", "Manager"])
        st.dataframe(feedback_df.set_index('Date'))
    else:
        st.info("No feedback has been provided for you yet.")

# --- Goal Management ---
elif page == "Goal Management":
    st.header("🎯 Goal Management")

    if is_manager:
        st.subheader("Set a New Goal for an Employee")
        employees_for_goals = [emp for emp in employees if not emp[2]] # Exclude managers
        employee_options_for_goals = {emp[1]: emp[0] for emp in employees_for_goals}
        
        if not employee_options_for_goals:
            st.warning("No employees found. Please add employees first.")
        else:
            with st.form("set_goal_form"):
                target_employee_name = st.selectbox("Select Employee", list(employee_options_for_goals.keys()))
                target_employee_id = employee_options_for_goals[target_employee_name]
                
                description = st.text_area("Goal Description")
                due_date = st.date_input("Due Date", value=date.today())
                
                submitted = st.form_submit_button("Set Goal")
                if submitted:
                    if description:
                        db_manager.create_goal(target_employee_id, selected_user_id, description, due_date)
                        st.success(f"Goal set for {target_employee_name}!")
                    else:
                        st.error("Please provide a goal description.")
    else:
        st.warning("Only managers can set and update goals.")
        
    st.markdown("---")
    st.subheader("Update Goal Status")
    
    # Show goals managed by the current user or assigned to them
    if is_manager:
        managed_goals = db_manager.read_goals(selected_user_id) # Read goals set for others
        goal_options = {f"Goal ID {g[0]} for {g[1]}": g[0] for g in managed_goals}
    else:
        my_goals = db_manager.read_goals(selected_user_id) # Read goals for self
        goal_options = {f"Goal ID {g[0]} ({g[1]})": g[0] for g in my_goals}

    if goal_options:
        selected_goal = st.selectbox("Select a goal to update", list(goal_options.keys()))
        selected_goal_id = goal_options[selected_goal]

        current_status_info = [g for g in (managed_goals if is_manager else my_goals) if g[0] == selected_goal_id][0]
        current_status = current_status_info[3]

        new_status = st.selectbox("New Status", ["Draft", "In Progress", "Completed", "Cancelled"], index=["Draft", "In Progress", "Completed", "Cancelled"].index(current_status))
        
        if st.button("Update Goal Status"):
            db_manager.update_goal_status(selected_goal_id, new_status)
            st.success("Goal status updated successfully!")
    else:
        st.info("No goals to update.")

# --- Feedback & History ---
elif page == "Feedback & History":
    st.header("Feedback and Performance History")
    
    st.subheader("Provide Written Feedback")
    if is_manager:
        employees_for_feedback = [emp for emp in employees if not emp[2]]
        employee_options_for_feedback = {emp[1]: emp[0] for emp in employees_for_feedback}

        if not employee_options_for_feedback:
            st.warning("No employees found to provide feedback for.")
        else:
            with st.form("provide_feedback_form"):
                target_employee_name = st.selectbox("Select Employee", list(employee_options_for_feedback.keys()))
                target_employee_id = employee_options_for_feedback[target_employee_name]
                
                # Fetch goals for selected employee
                goals_for_feedback = db_manager.read_goals(target_employee_id)
                if not goals_for_feedback:
                    st.warning(f"No goals found for {target_employee_name}. Please set a goal first.")
                else:
                    goal_options = {g[1]: g[0] for g in goals_for_feedback}
                    selected_goal_name = st.selectbox("Select Associated Goal", list(goal_options.keys()))
                    selected_goal_id = goal_options[selected_goal_name]
                    
                    comments = st.text_area("Your Feedback")
                    feedback_submitted = st.form_submit_button("Submit Feedback")
                    if feedback_submitted:
                        db_manager.create_feedback(selected_goal_id, target_employee_id, selected_user_id, comments)
                        st.success(f"Feedback submitted for {target_employee_name}!")
    else:
        st.warning("Only managers can provide written feedback.")

    st.markdown("---")
    st.subheader("Performance History")
    
    user_goals_history = db_manager.read_goals(selected_user_id)
    if user_goals_history:
        history_df = pd.DataFrame(user_goals_history, columns=["ID", "Description", "Due Date", "Status", "Manager"])
        st.dataframe(history_df.set_index('ID'))
    else:
        st.info("No goals in your history.")
    
# --- Business Insights ---
elif page == "Business Insights":
    st.header("📈 Business Insights")
    
    insights = db_manager.get_goal_insights()
    
    st.subheader("Goal Status Breakdown")
    if insights['status_counts']:
        status_df = pd.DataFrame(insights['status_counts'].items(), columns=["Status", "Count"])
        chart = alt.Chart(status_df).mark_bar().encode(
            x='Status',
            y='Count'
        ).properties(title='Goal Status Distribution')
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No goal data to analyze.")

    st.markdown("---")
    
    st.subheader("Performance Metrics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Average Days to Complete Goal", value=f"{insights['avg_days_to_complete']:.2f}")
    with col2:
        st.metric(label="Total Goals Tracked", value=sum(insights['status_counts'].values()) if insights['status_counts'] else 0)

    st.markdown("---")
    
    st.subheader("Manager Workload")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Min Goals per Manager", value=insights['min_goals_per_manager'])
    with col2:
        st.metric(label="Max Goals per Manager", value=insights['max_goals_per_manager'])