# backend_fin.py
import psycopg2
import streamlit as st

class DatabaseManager:
    """
    Manages all database operations for the Performance Management System.
    """
    def __init__(self, dbname, user, password, host, port):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn = None

    def connect(self):
        """Establishes a connection to the PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                dbname='Performance_db',
                user='postgres',
                password='Kiran2001##',
                host="localhost",
                port= "5432"
            )
        except psycopg2.OperationalError as e:
            st.error(f"Error connecting to database: {e}")
            self.conn = None

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

    def setup_database(self):
        """
        Creates the necessary tables and a trigger for automated feedback.
        Tables: employees, goals, feedback.
        """
        if not self.conn:
            return

        with self.conn.cursor() as cur:
            # Create employees table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    is_manager BOOLEAN DEFAULT FALSE
                );
            """)

            # Create goals table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id SERIAL PRIMARY KEY,
                    employee_id INT REFERENCES employees(id),
                    manager_id INT REFERENCES employees(id),
                    description TEXT NOT NULL,
                    due_date DATE NOT NULL,
                    status VARCHAR(50) DEFAULT 'Draft',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create feedback table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    goal_id INT REFERENCES goals(id),
                    employee_id INT REFERENCES employees(id),
                    manager_id INT REFERENCES employees(id),
                    comments TEXT NOT NULL,
                    feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create an automated feedback trigger function
            cur.execute("""
                CREATE OR REPLACE FUNCTION automated_feedback_trigger_function()
                RETURNS TRIGGER AS $$
                DECLARE
                    employee_name VARCHAR(255);
                BEGIN
                    IF NEW.status = 'Completed' AND OLD.status != 'Completed' THEN
                        SELECT name INTO employee_name FROM employees WHERE id = NEW.employee_id;
                        INSERT INTO feedback (goal_id, employee_id, manager_id, comments)
                        VALUES (
                            NEW.id,
                            NEW.employee_id,
                            NEW.manager_id,
                            'Goal "' || NEW.description || '" was successfully completed by ' || employee_name || '. Great work!'
                        );
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            # Create the trigger that fires on goal status updates
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'automated_feedback_trigger') THEN
                        CREATE TRIGGER automated_feedback_trigger
                        AFTER UPDATE ON goals
                        FOR EACH ROW
                        EXECUTE FUNCTION automated_feedback_trigger_function();
                    END IF;
                END
                $$;
            """)

            self.conn.commit()

    # --- CRUD Operations for Employees ---
    def create_employee(self, name, email, is_manager):
        """Adds a new employee/manager."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO employees (name, email, is_manager) VALUES (%s, %s, %s) RETURNING id;",
                            (name, email, is_manager))
                self.conn.commit()
                return cur.fetchone()[0]
        except psycopg2.IntegrityError:
            st.error("Error: An employee with this email already exists.")
            return None

    def read_employees(self):
        """Reads all employees."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name, is_manager FROM employees ORDER BY name;")
            return cur.fetchall()

    # --- CRUD Operations for Goals ---
    def create_goal(self, employee_id, manager_id, description, due_date):
        """Creates a new goal for an employee."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO goals (employee_id, manager_id, description, due_date)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (employee_id, manager_id, description, due_date))
            self.conn.commit()
            return cur.fetchone()[0]

    def read_goals(self, employee_id):
        """Reads all goals for a specific employee."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT g.id, g.description, g.due_date, g.status, e.name AS manager_name
                FROM goals g
                JOIN employees e ON g.manager_id = e.id
                WHERE g.employee_id = %s
                ORDER BY g.due_date DESC;
            """, (employee_id,))
            return cur.fetchall()

    def update_goal_status(self, goal_id, new_status):
        """Updates the status of a goal."""
        with self.conn.cursor() as cur:
            cur.execute("UPDATE goals SET status = %s, last_updated = CURRENT_TIMESTAMP WHERE id = %s;",
                        (new_status, goal_id))
            self.conn.commit()

    def delete_goal(self, goal_id):
        """Deletes a goal."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM goals WHERE id = %s;", (goal_id,))
            self.conn.commit()

    # --- CRUD Operations for Feedback ---
    def create_feedback(self, goal_id, employee_id, manager_id, comments):
        """Logs written feedback for an employee."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO feedback (goal_id, employee_id, manager_id, comments)
                VALUES (%s, %s, %s, %s);
            """, (goal_id, employee_id, manager_id, comments))
            self.conn.commit()

    def read_feedback(self, employee_id):
        """Reads all feedback for a specific employee."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT g.description AS goal_description, f.comments, f.feedback_date, m.name AS manager_name
                FROM feedback f
                JOIN goals g ON f.goal_id = g.id
                JOIN employees m ON f.manager_id = m.id
                WHERE f.employee_id = %s
                ORDER BY f.feedback_date DESC;
            """, (employee_id,))
            return cur.fetchall()

    # --- Business Insights ---
    def get_goal_insights(self):
        """Provides insights on goals using COUNT, AVG, MIN, MAX."""
        with self.conn.cursor() as cur:
            # Goal status counts
            cur.execute("SELECT status, COUNT(*) FROM goals GROUP BY status;")
            status_counts = dict(cur.fetchall())
            
            # Average time to complete a goal
            cur.execute("""
                SELECT AVG(EXTRACT(epoch FROM g.last_updated - g.due_date)) / 86400
                FROM goals g
                WHERE g.status = 'Completed';
            """)
            avg_days_to_complete = cur.fetchone()[0]

            # Min/Max goals per manager
            cur.execute("""
                SELECT MIN(goal_count), MAX(goal_count) FROM (
                    SELECT COUNT(*) AS goal_count FROM goals GROUP BY manager_id
                ) AS subquery;
            """)
            min_max_goals = cur.fetchone()

        return {
            'status_counts': status_counts,
            'avg_days_to_complete': avg_days_to_complete or 0,
            'min_goals_per_manager': min_max_goals[0] if min_max_goals and min_max_goals[0] is not None else 0,
            'max_goals_per_manager': min_max_goals[1] if min_max_goals and min_max_goals[1] is not None else 0
        }