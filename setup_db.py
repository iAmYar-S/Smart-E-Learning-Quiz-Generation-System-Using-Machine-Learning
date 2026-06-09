import mysql.connector

# Connect directly to Aiven
db = mysql.connector.connect(
    host="mysql-e113f01-slyvastianray02-1a38.h.aivencloud.com",
    user="avnadmin",
    password="AVNS_3RtHyQawA8CIzgvmRKZ", # Paste your password!
    port=16902,
    database="defaultdb"
)

cursor = db.cursor()

print("Creating tables in Aiven cloud...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    full_name VARCHAR(255),
    bio TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS quizzes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    generated_question TEXT NOT NULL,
    target_answer TEXT NOT NULL,
    options TEXT,
    type VARCHAR(50),
    share_code VARCHAR(10) NOT NULL,
    is_practice BOOLEAN DEFAULT 0,
    creator_email VARCHAR(255)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS student_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    score INT,
    total_questions INT,
    quiz_id INT,
    date_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
)
""")

print("Success! Tables created.")
cursor.close()
db.close()