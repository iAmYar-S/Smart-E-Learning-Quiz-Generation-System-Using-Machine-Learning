import google.generativeai as genai
import json
import os  # Added to access system environment variables

# ==========================================
# 1. CONFIGURE THE AI SECURELY
# ==========================================
# Pulls directly from the Render Environment variables in production,
# preventing accidental public leaks on GitHub.
YOUR_API_KEY = os.environ.get("GEMINI_API_KEY")

if not YOUR_API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not found!")

genai.configure(api_key=YOUR_API_KEY)

# Using Gemini 2.5 Flash for lightning-fast processing of massive PDFs
model = genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# 2. CORE GENERATOR
# ==========================================
def generate_multiple_quizzes(context_text, q_type="mcq", num_questions=5):
    """
    Passes the PDF text to a Generative LLM with strict instructions 
    to create complex, multi-layered academic questions.
    """
    
    # Alter the instructions based on the selected question format
    format_instruction = ""
    if q_type == "mcq":
        format_instruction = """
        - "options": A list of exactly 4 choices. CRITICAL RULE: Keep every single option very concise (maximum one short sentence). Ensure strictly ONLY ONE option is the correct answer, and the other three are definitively incorrect distractors.
        """
    elif q_type == "tf":
        format_instruction = """
        - "options": Exactly ["True", "False"]. The question should be a complex statement that requires deep understanding to evaluate.
        """
    else:
        format_instruction = """
        - "options": null. Do not provide multiple choice options.
        """

    # This prompt forces the AI to act as an expert professor and return clean JSON
    prompt = f"""
    You are an expert university professor creating an exam based strictly on the provided text.
    Your goal is to generate {num_questions} high-quality, complex questions.
    
    Rules:
    1. Test deep understanding of processes, relationships, and "how/why", not just simple vocabulary definitions.
    2. Do NOT use silly or obvious wrong answers.
    3. Ensure the correct answer is 100% supported by the text context.
    4. You MUST return your output ONLY as a valid JSON array of objects.
    
    Expected JSON Structure:
    [
      {{
        "question": "The complex question text...",
        "answer": "The exact correct answer from the options",
        {format_instruction}
      }}
    ]

    Here is the reading material:
    ---
    {context_text}
    """

    try:
        # Ask the AI to read the text and FORCE it to return perfect JSON
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        clean_text = response.text.strip()
        
        # Parse the JSON string back into Python dictionaries (strict=False ignores hidden characters)
        quiz_data = json.loads(clean_text, strict=False)
        
        # Ensure we always return a list
        if not isinstance(quiz_data, list):
            quiz_data = [quiz_data]
            
        return quiz_data

    except Exception as e:
        print(f"AI Generation Error: {e}")
        # Return a safe error format so the app doesn't crash
        return [
            {
                "question": f"Error generating quiz: Please check terminal. {str(e)}", 
                "answer": "Error", 
                "options": ["Error", "Error", "Error", "Error"]
            }
        ]