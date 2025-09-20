-- Create the employees table to store user information.
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    is_manager BOOLEAN DEFAULT FALSE
);

-- Create the goals table to store performance goals.
CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    employee_id INT REFERENCES employees(id),
    manager_id INT REFERENCES employees(id),
    description TEXT NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'Draft',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the feedback table to store written and automated feedback.
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    goal_id INT REFERENCES goals(id),
    employee_id INT REFERENCES employees(id),
    manager_id INT REFERENCES employees(id),
    comments TEXT NOT NULL,
    feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a PL/pgSQL function to automate feedback when a goal is completed.
CREATE OR REPLACE FUNCTION automated_feedback_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    employee_name VARCHAR(255);
BEGIN
    -- Check if the goal status has changed to 'Completed' from a different status.
    IF NEW.status = 'Completed' AND OLD.status != 'Completed' THEN
        -- Get the employee's name for the feedback message.
        SELECT name INTO employee_name FROM employees WHERE id = NEW.employee_id;
        
        -- Insert a new feedback record.
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

-- Create the trigger that fires the function after a goal update.
DO $$
BEGIN
    -- Check if the trigger already exists to prevent errors on re-running the script.
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'automated_feedback_trigger') THEN
        CREATE TRIGGER automated_feedback_trigger
        AFTER UPDATE ON goals
        FOR EACH ROW
        EXECUTE FUNCTION automated_feedback_trigger_function();
    END IF;
END
$$;